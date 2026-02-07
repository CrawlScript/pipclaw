import os
from .config import ConfigManager
from .kernel import PipClaw
from .connectors import TelegramConnector, TerminalConnector, WhatsAppConnector

def setup_wizard():
    print("\n--- 🐈 PipClaw Setup Wizard ---")
    config = ConfigManager.DEFAULT_CONFIG.copy()

    # 1. LLM Configuration
    print("\n[1/3] LLM Engine Setup")
    api_key = input("Enter your OpenAI/DeepSeek API Key: ").strip()
    if api_key:
        config["api_key"] = api_key
    
    base_url = input("Enter Base URL (default: https://api.deepseek.com): ").strip()
    if base_url:
        config["base_url"] = base_url

    # 2. Mode Selection
    print("\n[2/3] Interaction Mode")
    print("1. Terminal Mode")
    print("2. Telegram Mode")
    print("3. WhatsApp Mode (Scan QR Code)")
    choice = input("Select mode (1, 2, or 3): ").strip()

    if choice == "2":
        config["preferred_mode"] = "telegram"
        print("\n--- 🛠 Telegram Setup ---")
        config["telegram_token"] = input("Bot API Token: ").strip()
        user_id = input("Your User ID: ").strip()
        config["authorized_user_id"] = int(user_id) if user_id.isdigit() else 0
    elif choice == "3":
        config["preferred_mode"] = "whatsapp"
        print("\n--- 🛠 WhatsApp Setup ---")
        print("[*] No tokens needed. You will scan a QR code in your terminal on run.")
    else:
        config["preferred_mode"] = "terminal"

    # 3. Save
    ConfigManager.save(config)
    return config

def main():
    config = ConfigManager.load()
    
    if not config:
        config = setup_wizard()

    # Mode Dispatch
    mode = config.get("preferred_mode")
    if mode == "telegram":
        connector = TelegramConnector(config["telegram_token"], config["authorized_user_id"])
    elif mode == "whatsapp":
        connector = WhatsAppConnector()
    else:
        connector = TerminalConnector()

    if config["api_key"] == "sk-your-key-here":
        print(f"\n[❌] API Key missing. Please run again or edit {ConfigManager.CONFIG_FILE}")
        return
    
    app = PipClaw(config, connector, system_prompt=ConfigManager.get_full_prompt())
    app.run()

if __name__ == "__main__":
    main()