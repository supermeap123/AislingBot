import re
import random

TRIGGER_WORDS = ["aisling", "a!", "aisling#2534"]  # Replace XXXX with the actual discriminator

def contains_trigger_word(content):
    return any(word in content.lower() for word in TRIGGER_WORDS)

def is_bot_mentioned(message, bot_user):
    return bot_user.mentioned_in(message)

def random_chance(probability):
    return random.random() < probability

def replace_usernames_with_mentions(content, guild):
    # Implement logic to replace usernames with mentions
    return content

def replace_ping_with_mention(content, user):
    return content.replace('*ping*', user.mention)

def replace_name_exclamation_with_mention(content, user):
    pattern = re.compile(r'\b{}!\b'.format(re.escape(user.display_name)), re.IGNORECASE)
    return pattern.sub(user.mention, content)

def is_valid_prefix(prefix):
    return len(prefix) <= 5  # Example validation