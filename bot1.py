from telethon import TelegramClient, events
from telethon.tl.types import InputMediaPhoto
import json
import re
import time
import requests
from telethon.sessions import StringSession

# تحميل البيانات من Gist
def load_data():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
    if response.status_code == 200:
        files = response.json().get('files', {})
        content = files.get('data2702.json', {}).get('content', '{}')
        return json.loads(content)
    else:
        return {}

data = load_data()
source_destination_mapping = {
    int(key): [int(channel_id) for channel_id in value]
    for key, value in data.get("source_destination_mapping", {}).items()
}

words_to_remove = data.get("words_to_remove", [])
lines_to_remove_starting_with = data.get("lines_to_remove_starting_with", [])
sentence_replacements = data.get("sentence_replacements", {})
line_replacements = data.get("line_replacements", {})
ignored_words = data.get("ignored_words", [])
ignored_users = [15966619410, 9876543210]

session = data.get("session", [])
session_string = session or "1BJWap1sBu5x6qA8INQIhnJ7zsfmoc2KaJ6ryx7EzU5z7IeB21pOjf5lpT-4xsRowocH7eld0HXHrjFnSCXyvSMgW4RKpN-dMYyW_aZRUnJb3CSPLySVeM2iqgeL61ZY79eRQDJGNo8BSnchpkeGf83w4U1GXWHZp95rLPHAUKwC3UJCSMvQv4mTGCjC7uHoV2QWsV_jEAQFEM4OtKIzOqySkVDttvTSDfrxh4ic9-3J_SLQkneaPj4oG1cHJEoKHrWuksNL6Z0C-4TjuBoCOOPRbdK_648rfAut47s6RW0yXTWyt3XIXLCZWPW7EPIjlTKdLGUrkQxaJ4U7l1s8MSQHJ--ZaCoo="

# إعدادات Telethon
api_id = 23068290
api_hash = 'e38697ea4202276cbaa91d20b99af864'
client = TelegramClient(StringSession(session_string), api_id, api_hash)

app1 = client

# دوال معالجة النصوص
def remove_empty_lines(text):
    lines = text.split("\n")
    return "\n".join(line for line in lines if line.strip())

word_patterns_to_remove = [re.compile(re.escape(word)) for word in words_to_remove]
line_patterns_to_remove_starting_with = [re.compile("^" + re.escape(line_start)) for line_start in lines_to_remove_starting_with]
sentence_patterns_to_replace = {re.compile(re.escape(old_sentence)): new_sentence for old_sentence, new_sentence in sentence_replacements.items()}
line_patterns_to_replace = {re.compile("^" + re.escape(old_line)): new_line for old_line, new_line in line_replacements.items()}

def remove_lines_starting_with(text, pattern):
    return "\n".join(line for line in text.split("\n") if not pattern.match(line))

def replace_lines_starting_with(text, pattern, replacement):
    return "\n".join(replacement if pattern.match(line) else line for line in text.split("\n"))

async def preprocess_message_with_regex(message_text):
    text = message_text or ""

    # إزالة الكلمات المحظورة
    for pattern in word_patterns_to_remove:
        text = pattern.sub("", text)

    # إزالة الأسطر التي تبدأ بكلمات معينة
    for pattern in line_patterns_to_remove_starting_with:
        text = remove_lines_starting_with(text, pattern)

    # استبدال الجمل
    for pattern, replacement in sentence_patterns_to_replace.items():
        text = pattern.sub(replacement, text)

    # استبدال الأسطر
    for pattern, replacement in line_patterns_to_replace.items():
        text = replace_lines_starting_with(text, pattern, replacement)

    # إزالة الأسطر الفارغة
    text = remove_empty_lines(text.strip())

    return text

@app1.on(events.NewMessage(chats=list(source_destination_mapping.keys())))
async def copy_message(event):
    try:
        # تجاهل المستخدمين المحظورين
        if event.sender_id in ignored_users:
            return
            
        message_text = event.message.message or ""
        
        # التحقق من وجود كلمات محظورة
        if any(word in message_text for word in ignored_words):
            print(f"Ignoring message with restricted words: {message_text}")
            return

        source_channel_id = event.chat_id
        dest_channels = source_destination_mapping.get(source_channel_id, [])

        # إذا كانت الرسالة جزءًا من مجموعة وسائط
        if event.grouped_id:
            time.sleep(5)
            if event.grouped_id in processed_media_groups:
                return

            processed_media_groups.add(event.grouped_id)

            media_group = await event.client.get_messages(
                event.chat_id, 
                ids=[msg.id for msg in await event.client.get_messages(event.chat_id, limit=20) if msg.grouped_id == event.grouped_id]
            )

            media_files = []
            caption = ""
            for msg in media_group:
                if not caption and msg.message:
                    caption = await preprocess_message_with_regex(msg.message)

                if msg.media:
                    media_files.append(msg.media)

            for dest_channel_id in dest_channels:
                await app1.send_file(dest_channel_id, media_files, caption=caption)
        else:
            caption = await preprocess_message_with_regex(event.message.message or "")
            for dest_channel_id in dest_channels:
                if event.message.media:
                    await app1.send_file(dest_channel_id, event.message.media, caption=caption)
                else:
                    await app1.send_message(dest_channel_id, caption)

    except Exception as e:
        print(f"Error: {e}")

print("bot1 starting")
