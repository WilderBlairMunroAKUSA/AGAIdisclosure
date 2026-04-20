#!/usr/bin/env python3
import json
import os
import re
from datetime import datetime, timezone
"""
Ugly oneoff patchwork script to get conversation exports into one place,
outputting json files per conversation within directories './_conversations_*'.
Exclusions: qwen, duckai, local model testing (llama et al).
Minimal PII sanitized (direct name mentions only).

"""

# ==== IMPORT FUNCTIONS ========================
def import_conversations_openai():
    os.makedirs(f"_conversations_openai_raw", exist_ok=True)
    with open("_import_conversations/_conversations_openai.json", "r", encoding="utf-8") as f:
        unredacted_conversations = json.load(f) 

    def redact(obj):
        with open("_import_conversations/_redactlist🔒.json", "r", encoding="utf-8") as f:
            redactlist = json.load(f)
        # for name in redactlist["names"]:
        #     print(name)
        replacement = "..."
        names = [n for n in redactlist['names']]
        pattern = re.compile(
            r'\b(' + '|'.join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r')\b',
            re.IGNORECASE
        )
        def walk_and_redact(obj):
            """Recursively walk JSON structure, redact string values."""
            if isinstance(obj, dict):
                return {k: walk_and_redact(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [walk_and_redact(item) for item in obj]
            elif isinstance(obj, str):
                return pattern.sub(replacement, obj)
            return obj
        return walk_and_redact(obj)

    conversations = redact(unredacted_conversations)
    conversations.sort(key=lambda c: c["create_time"])
    for index, convo in enumerate(conversations):
        created = datetime.fromtimestamp(convo["create_time"], timezone.utc).strftime("%y%m%d")
        filename = f"{index+1:03d}-wilderblairmunroakusa-chatgpt-{created}.json"
        filepath = os.path.join(f"_conversations_openai_raw", filename)
        with open(filepath, "w", encoding="utf-8") as output_file:
            json.dump(convo, output_file, ensure_ascii=False, indent=2)

    print(f"✅ Imported {len(conversations)} OpenAI conversations.")
    return


def import_conversations_anthropic():
    os.makedirs(f"_conversations_anthropic_raw", exist_ok=True)
    with open("_import_conversations/_conversations_anthropic.json", "r", encoding="utf-8") as f:
        conversations = json.load(f) 
    with open("_import_conversations/_conversations_anthropic_titles.json", "r", encoding="utf-8") as f:
        titles = json.load(f) 

    conversations.sort(key=lambda c: c["created_at"])
    conversations = [c for c in conversations if c["name"] in titles] # remove temp convos
    for index, convo in enumerate(conversations):
        created = datetime.fromisoformat(convo["created_at"].replace("Z", "+00:00")).strftime("%y%m%d")
        filename = f"{index+1:03d}-wilderblairmunroakusa-claude-{created}.json"
        filepath = os.path.join(f"_conversations_anthropic_raw", filename)
        with open(filepath, "w", encoding="utf-8") as output_file:
            json.dump(convo, output_file, ensure_ascii=False, indent=2)

    print(f"✅ Imported {len(conversations)} Anthropic conversations.")
    return


def import_conversations_xai():
    os.makedirs(f"_conversations_xai_raw", exist_ok=True)
    with open("_import_conversations/_conversations_xai.json", "r", encoding="utf-8") as f:
        conversations = json.load(f) 

    conversations = conversations["conversations"]
    conversations.sort(key=lambda c: c["conversation"]["create_time"])
    for index, convo in enumerate(conversations):
        created = datetime.fromisoformat(convo["conversation"]["create_time"].replace("Z", "+00:00")).strftime("%y%m%d")
        filename = f"{index+1:03d}-wilderblairmunroakusa-grok-{created}.json"
        filepath = os.path.join(f"_conversations_xai_raw", filename)
        with open(filepath, "w", encoding="utf-8") as output_file:
            json.dump(convo, output_file, ensure_ascii=False, indent=2)

    print(f"✅ Imported {len(conversations)} xAI conversations.")
    return


def import_conversations_google():
    os.makedirs(f"_conversations_google_raw", exist_ok=True)
    with open("_import_conversations/_conversations_google.md", "r", encoding="utf-8") as f:
        conversation_blob = f.read()

    datestring_pairs = []
    for path in [
        "_import_conversations/_conversations_google_wilder.html",
        "_import_conversations/_conversations_google_bmakusa.html"
        ]:
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        pattern = r'<br>([^<]*?)AKDT<br><hr>\n<p>(.*?)</p>'
        datestring_pairs.extend([list(m) for m in re.findall(pattern, html, re.DOTALL)])
        pattern = r'<br>([^<]*?)AKDT<br><p>(.*?)</p>'
        datestring_pairs.extend([list(m) for m in re.findall(pattern, html, re.DOTALL)])
        pattern = r'<br>([^<]*?)AKDT<br><h3>(.*?)</h3>'
        datestring_pairs.extend([list(m) for m in re.findall(pattern, html, re.DOTALL)])
        pattern = r'<br>([^<]*?)AKDT<br><hr>\n<h3>(.*?)</h3>'
        datestring_pairs.extend([list(m) for m in re.findall(pattern, html, re.DOTALL)])

    # massage
    datestring_pairs = [[m[0], m[1].replace(":) 💜", "smilepurpleheart").replace("quot;", ";").replace("strong>", ">").replace("em>", ">").replace("code>", ">").replace("br>", ">")] for m in datestring_pairs]
    # condition
    datestring_pairs = [[m[0], re.sub(r'[^a-z]', '', m[1].lower())] for m in datestring_pairs]  
    for string in datestring_pairs:
        string[0] = datetime.strptime(string[0], "%b %d, %Y, %I:%M:%S\u202f%p ").strftime("%Y-%m-%d %H:%M:%S %b %a")

    conversation_blob = conversation_blob.split("""#CONVERSATION ==============================================
""")[1:]

    conversations = []
    for convo in conversation_blob:
        convo = convo.split("\n")
        conversation = {}
        conversation["title"] = convo[0].split("#TITLE: ")[1].replace("\"", "")
        conversation["datetime"] = datetime.strptime(convo[1].split("#DATE: ")[1], "\"%B %d, %Y at %I:%M %p\"").strftime("%Y-%m-%d %H:%M:%S %b %a")
        conversation["model"] = convo[2].split("#MODEL: ")[1].replace("\"", "")
        turnpairs = []
        turnpair_current = []
        start = next(i for i, line in enumerate(convo[3:]) if line == '## Prompt:')
        for line in convo[3 + start:]:
            if line == '## Prompt:':
                turnpairs.append(turnpair_current)
                turnpair_current = []
            else:
                turnpair_current.append(line)
        turnpairs.append(turnpair_current)

        turns = []
        for index, turnpair in enumerate(turnpairs[1:]):
            turn = []
            turn_current = []
            for line in turnpair:
                if line == '## Response:':
                    turn.append('\n'.join(turn_current))
                    turn_current = []
                else:
                    turn_current.append(line)
            turn.append('\n'.join(turn_current))
            turns.append(turn)
        conversation["turnpairs"] = [
            {"user": u, "assistant": a}
            for u, a in turns
        ]
        conversations.append(conversation)

    for conversation in conversations:
        for turnpair in conversation["turnpairs"]:
            text = turnpair["assistant"]
            text = text.replace(":) 💜", "smilepurpleheart").replace("* * *\n\n", "")
            for match in datestring_pairs:
                firstline = re.sub(r'[^a-z]', '', text.split("\n")[0].lower())
                if firstline[0:55] == match[1][0:55]:
                    turnpair["datetime"] = match[0]

    conversations.sort(key=lambda c: c["datetime"])
    for index, convo in enumerate(conversations):
        created = datetime.strptime(convo["datetime"], "%Y-%m-%d %H:%M:%S %b %a").strftime("%y%m%d")
        filename = f"{index+1:03d}-wilderblairmunroakusa-gemini-{created}.json"
        filepath = os.path.join(f"_conversations_google_raw", filename)
        with open(filepath, "w", encoding="utf-8") as output_file:
            json.dump(convo, output_file, ensure_ascii=False, indent=2)

    print(f"✅ Imported {len(conversations)} Google conversations.")
    return



# ==== MAIN ========================
def main():

    import_conversations_openai()
    import_conversations_anthropic()
    import_conversations_xai()
    import_conversations_google()

if __name__ == "__main__":
    main()