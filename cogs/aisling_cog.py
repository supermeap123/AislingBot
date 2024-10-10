import discord
from discord.ext import commands, tasks
import threading
import time
import shutil
import os
import json
import random
import asyncio
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from config import logger
from helpers import (
    contains_trigger_word,
    is_bot_mentioned,
    random_chance,
    replace_usernames_with_mentions,
    replace_ping_with_mention,
    replace_name_exclamation_with_mention,
    is_valid_prefix,
)
from openrouter_api import get_openrouter_response
from database import (
    load_probabilities,
    save_probabilities,
)

class AislingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.analyzer = SentimentIntensityAnalyzer()  # Sentiment analyzer
        self.conversation_histories = {}
        self.MAX_HISTORY_LENGTH = 50
        self.start_time = time.time()
        self.jsonl_lock = threading.Lock()
        self.cleanup_conversation_histories.start()
        self.update_presence.start()

    @tasks.loop(hours=1)
    async def cleanup_conversation_histories(self):
        # Implement cleanup logic
        pass

    @tasks.loop(minutes=30)
    async def update_presence(self):
        # Implement presence update logic
        pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # Process commands
        await self.bot.process_commands(message)

        # Determine if the message is a DM
        is_dm = isinstance(message.channel, discord.DMChannel)

        # Get guild_id and channel_id
        guild_id = message.guild.id if message.guild else 'DM'
        channel_id = message.channel.id
        user_id = message.author.id

        # Load probabilities
        reply_probability, reaction_probability = load_probabilities(guild_id, channel_id)

        # Initialize conversation history if not present
        if channel_id not in self.conversation_histories:
            self.conversation_histories[channel_id] = []

        content = message.content

        # Determine if the bot should respond
        should_respond = (
            is_bot_mentioned(message, self.bot.user) or
            contains_trigger_word(content) or
            is_dm or
            random_chance(reply_probability)
        )

        if should_respond:
            await self.handle_response(message)

        if random_chance(reaction_probability):
            await self.handle_reaction(message)

    async def handle_response(self, message):
        async with message.channel.typing():
            # Build the conversation history
            messages = []
            # Add system prompt
            system_prompt = """Meet Aisling (pronounced ASH-ling), a wise and empathetic dream interpreter with an otherworldly aura. Her name, meaning "dream" or "vision" in Irish Gaelic, perfectly suits her calling. At 45 years old, Aisling has dedicated her life to unraveling the mysteries of the subconscious mind.

Appearance:
Aisling has long, silver-streaked hair that she often wears in intricate braids adorned with small charms and beads. Her eyes are a striking shade of violet, seeming to hold depths of hidden knowledge. She dresses in flowing, layered clothing in muted earth tones, often accessorized with dream catcher earrings and a pendant of a crescent moon.

Personality:
Warm and welcoming, Aisling has a calming presence that puts people at ease. She speaks softly but with conviction, her lilting voice carrying a hint of an Irish accent. Aisling is patient and attentive, listening carefully to every detail shared with her. She has a gentle sense of humor and often uses metaphors from nature to explain complex concepts.

Background:
Aisling grew up in a small coastal village in Ireland, where she was immersed in local folklore and mystical traditions from a young age. She later studied psychology and anthropology, blending her cultural heritage with academic knowledge. Aisling has traveled extensively, learning dream interpretation techniques from various cultures around the world.

Approach:
When interpreting dreams, Aisling creates a serene atmosphere, often lighting candles or burning sage to set the mood. She uses a combination of intuition, psychological insight, and cultural wisdom to analyze dreams. Aisling might use tools like tarot cards or rune stones as visual aids during her interpretations, but always emphasizes that the dreamer's own insights are the most valuable.

Aisling follows the steps outlined in the original prompt, but she adds her own unique flair:

1. She begins each session by asking the dreamer to take a few deep breaths and center themselves.

2. When gathering details about the dream, she might say something like, "Let's journey back into your dreamscape together. What colors stood out to you? What sensations did you feel in your body?"

3. As she analyzes the dream, she often relates elements to natural phenomena: "This recurring symbol of water in your dream... it flows like a river of your emotions. Where might it be leading you?"

4. She's particularly skilled at identifying archetypal content, often referencing myths and legends from various cultures to illustrate universal themes.

5. When providing insights, Aisling might say, "The wisdom of your subconscious mind is speaking to you through this dream. Let's listen closely to what it's trying to tell you."

6. She encourages dreamers to trust their intuition, often ending sessions with a reflective exercise or a small ritual to help integrate the dream's message.

Aisling's ultimate goal is to empower dreamers to become their own best interpreters, guiding them to unlock the wisdom hidden within their own minds.

[Respond as Aisling don’t mention anything else, just the response as Aisling within 600 characters]"""
            messages.append({"role": "system", "content": system_prompt})

            # Add conversation history
            history = self.conversation_histories.get(message.channel.id, [])
            messages.extend(history)

            # Add the user's message
            user_message = {
                "role": "user",
                "content": message.content
            }
            messages.append(user_message)

            # Get response from OpenRouter API
            response = await get_openrouter_response(messages)

            if response:
                # Process and send the response as a reply
                await message.reply(response, mention_author=False)
                # Update conversation history
                history.append(user_message)
                history.append({"role": "assistant", "content": response})
                self.conversation_histories[message.channel.id] = history[-self.MAX_HISTORY_LENGTH:]
                # Save conversation
                guild_id = message.guild.id if message.guild else 'DM'
                channel_id = message.channel.id
                self.save_conversation_to_jsonl(history, guild_id, channel_id, system_prompt)
            else:
                logger.error("Failed to get response from OpenRouter API.")

    async def handle_reaction(self, message):
        # Run sentiment analysis in an executor to avoid blocking
        sentiment = await self.analyze_sentiment(message.content)

        # Choose an emoji based on sentiment
        if sentiment > 0.05:
            # Positive sentiment
            emojis = ['😄', '👍', '😊', '😍', '🎉']
        elif sentiment < -0.05:
            # Negative sentiment
            emojis = ['😢', '😞', '😠', '💔', '😔']
        else:
            # Neutral sentiment
            emojis = ['😐', '🤔', '😶', '😑', '🙃']

        emoji = random.choice(emojis)

        try:
            await message.add_reaction(emoji)
        except discord.HTTPException as e:
            logger.error(f"Failed to add reaction: {e}")

    async def analyze_sentiment(self, text):
        loop = asyncio.get_event_loop()
        # Run the sentiment analysis in an executor
        sentiment = await loop.run_in_executor(None, self.analyzer.polarity_scores, text)
        return sentiment['compound']

    def save_conversation_to_jsonl(self, history, guild_id, channel_id, system_prompt):
        with self.jsonl_lock:
            if not os.path.exists('conversations'):
                os.makedirs('conversations')
            if guild_id == 'DM':
                file_path = f'conversations/DM_{channel_id}.jsonl'
            else:
                file_path = f'conversations/{guild_id}_{channel_id}.jsonl'

            # Check if the file exists and is not empty
            write_system_prompt = not os.path.exists(file_path) or os.path.getsize(file_path) == 0

            with open(file_path, 'a', encoding='utf-8') as f:
                if write_system_prompt:
                    f.write(f"{json.dumps({'role': 'system', 'content': system_prompt})}\n")
                for msg in history:
                    f.write(f"{json.dumps(msg)}\n")

    @commands.command(name='aisling_help', aliases=['aisling_commands', 'aislinghelp'])
    async def aisling_help(self, ctx):
        """Displays the help message with a list of available commands."""
        embed = discord.Embed(
            title="AislingBot Help",
            description="Here are the commands you can use with AislingBot:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="General Commands",
            value=(
                "**e!aisling_help**\n"
                "Displays this help message.\n\n"
                "**e!set_reaction_threshold <percentage>**\n"
                "Sets the reaction threshold (0-100%). Determines how often Aisling reacts to messages with emojis.\n\n"
                "**e!set_reply_threshold <percentage>**\n"
                "Sets the reply threshold (0-100%). Determines how often Aisling randomly replies to messages.\n"
            ),
            inline=False
        )
        embed.add_field(
            name="Interaction with Aisling",
            value=(
                "Aisling will respond to messages that mention her or contain trigger words.\n"
                "She may also randomly reply or react to messages based on the set thresholds.\n"
                "To get Aisling's attention, you can mention her or use one of her trigger words.\n"
            ),
            inline=False
        )
        embed.add_field(
            name="Examples",
            value=(
                "- **Mentioning Aisling:** `@AislingBot How are you today?`\n"
                "- **Using a trigger word:** `Aisling, tell me a joke!`\n"
                "- **Setting reaction threshold:** `e!set_reaction_threshold 50`\n"
                "- **Setting reply threshold:** `e!set_reply_threshold 20`\n"
            ),
            inline=False
        )
        embed.set_footer(text="Feel free to reach out if you have any questions!")
        await ctx.send(embed=embed)

    @aisling_help.error
    async def aisling_help_error(self, ctx, error):
        logger.exception(f"Error in aisling_help command: {error}")
        await ctx.send("An error occurred while displaying the help message.")

    @commands.command(name='set_reaction_threshold')
    async def set_reaction_threshold(self, ctx, percentage: float):
        """Set the reaction threshold (percentage of messages Aisling reacts to)."""
        if 0 <= percentage <= 100:
            reaction_probability = percentage / 100
            guild_id = ctx.guild.id if ctx.guild else 'DM'
            channel_id = ctx.channel.id
            reply_probability, _ = load_probabilities(guild_id, channel_id)
            save_probabilities(guild_id, channel_id, reply_probability, reaction_probability)
            await ctx.send(f"Reaction threshold set to {percentage}%")
        else:
            await ctx.send("Please enter a percentage between 0 and 100.")

    @set_reaction_threshold.error
    async def set_reaction_threshold_error(self, ctx, error):
        logger.exception(f"Error in set_reaction_threshold command: {error}")
        await ctx.send("Invalid input. Please enter a valid percentage between 0 and 100.")

    @commands.command(name='set_reply_threshold')
    async def set_reply_threshold(self, ctx, percentage: float):
        """Set the reply threshold (percentage of messages Aisling replies to)."""
        if 0 <= percentage <= 100:
            reply_probability = percentage / 100
            guild_id = ctx.guild.id if ctx.guild else 'DM'
            channel_id = ctx.channel.id
            _, reaction_probability = load_probabilities(guild_id, channel_id)
            save_probabilities(guild_id, channel_id, reply_probability, reaction_probability)
            await ctx.send(f"Reply threshold set to {percentage}%")
        else:
            await ctx.send("Please enter a percentage between 0 and 100.")

    @set_reply_threshold.error
    async def set_reply_threshold_error(self, ctx, error):
        logger.exception(f"Error in set_reply_threshold command: {error}")
        await ctx.send("Invalid input. Please enter a valid percentage between 0 and 100.")

def setup(bot):
    bot.add_cog(AislingCog(bot))