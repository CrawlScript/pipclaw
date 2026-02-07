const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason,
} = require("@whiskeysockets/baileys");
const qrcode = require("qrcode-terminal");
const pino = require("pino");
const fs = require("fs");
const path = require("path");
const os = require("os");

async function startBot() {
    const sessionDir = path.join(os.homedir(), ".pipclaw", "wa_auth");
    if (!fs.existsSync(path.dirname(sessionDir))) {
        fs.mkdirSync(path.dirname(sessionDir), { recursive: true });
    }
    const { state, saveCreds } = await useMultiFileAuthState(sessionDir);

    const sock = makeWASocket({
        auth: state,
        logger: pino({ level: "silent" }),
        printQRInTerminal: false,
    });

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", (update) => {
        const { connection, lastDisconnect, qr } = update;
        
        if (qr) {
            console.log("\n--- SCAN THIS QR CODE WITH WHATSAPP ---");
            qrcode.generate(qr, { small: true });
        }

        if (connection === "close") {
            const shouldReconnect = lastDisconnect.error?.output?.statusCode !== DisconnectReason.loggedOut;
            if (shouldReconnect) startBot();
        } else if (connection === "open") {
            console.log("JSON_EVENT:" + JSON.stringify({ 
                type: "connected", 
                me: sock.user.id 
            }));
        }
    });

    sock.ev.on("messages.upsert", async (m) => {
        if (m.type === "notify") {
            for (const msg of m.messages) {
                const jid = msg.key.remoteJid;
                if (jid === "status@broadcast") continue;

                // Better text extraction
                const text = msg.message?.conversation || 
                             msg.message?.extendedTextMessage?.text || 
                             msg.message?.buttonsResponseMessage?.selectedButtonId ||
                             msg.message?.listResponseMessage?.singleSelectReply?.selectedRowId ||
                             "";

                if (text) {
                    console.log("JSON_EVENT:" + JSON.stringify({
                        type: "message",
                        from: jid,
                        text: text,
                        fromMe: msg.key.fromMe,
                        pushName: msg.pushName || ""
                    }));
                }
            }
        }
    });

    process.stdin.on("data", async (data) => {
        try {
            const line = data.toString().trim();
            if (line.startsWith("SEND:")) {
                const payload = JSON.parse(line.substring(5));
                await sock.sendMessage(payload.to, { text: payload.text });
            }
        } catch (e) {
            // Error handling
        }
    });
}

startBot();
