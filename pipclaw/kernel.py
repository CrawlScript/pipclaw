import threading
import queue
import json
import re
from .providers import Engine
from .tools import ShellTool, FileTool

class Memory(object):
    def __init__(self, system_prompt):
        self.history = [{"role": "system", "content": system_prompt}]
    def add(self, role, content): self.history.append({"role": role, "content": content})
    def get_all(self): return self.history

class PipClaw(object):
    def __init__(self, config, connector, system_prompt):
        self.engine = Engine(config)
        self.connector = connector
        self.memory = Memory(system_prompt)
        self.task_queue = queue.Queue()
        
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _extract_json(self, text):
        """Finds and parses the first JSON block from text."""
        # Strip markdown code blocks if present
        text = re.sub(r'```json\s*(.*?)\s*```', r'\1', text, flags=re.DOTALL)
        
        try:
            start_idx = text.find('{')
            if start_idx != -1:
                # Use JSONDecoder to find the first complete JSON object
                decoder = json.JSONDecoder()
                obj, _ = decoder.raw_decode(text[start_idx:])
                return obj
        except Exception:
            return None
        return None

    def _worker(self):
        while True:
            user_text = self.task_queue.get()
            if user_text is None: break
            
            self.memory.add("user", user_text)
            
            while True:
                response_msg = self.engine.ask(self.memory.get_all())
                raw_text = response_msg.get("content", "")
                
                # We save the raw response to memory to maintain context
                self.memory.add("assistant", raw_text)

                data = self._extract_json(raw_text)
                if not data:
                    self.connector.send(raw_text)
                    break

                if data.get("content"):
                    self.connector.send(data["content"])

                tools = data.get("tools", [])
                if not tools:
                    break

                for tool in tools:
                    name = tool.get("name")
                    args = tool.get("args", {})
                    
                    result = ""
                    if name == "shell_execute":
                        self.connector.send(f"🐚 Shell: `{args.get('command')}`")
                        result = ShellTool.execute(args.get("command"))
                    elif name == "file_read":
                        self.connector.send(f"📖 Read: `{args.get('path')}`")
                        result = FileTool.read(args.get("path"))
                    elif name == "file_write":
                        self.connector.send(f"💾 Write: `{args.get('path')}`")
                        result = FileTool.write(args.get("path"), args.get("content"))
                    elif name == "file_upload":
                        self.connector.send(f"📤 Upload: `{args.get('path')}`")
                        self.connector.send_file(args.get("path"))
                        result = f"File {args.get('path')} sent."
                    
                    self.memory.add("system", f"Tool Output ({name}):\n{result}")

            self.task_queue.task_done()

    def handle(self, text):
        self.task_queue.put(text)

    def run(self):
        self.connector.listen(self.handle)
