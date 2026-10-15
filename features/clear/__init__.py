import discord
from discord.ext import commands


class Clear(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="clear", aliases=["purge", "cl"])
    @commands.is_owner()
    async def clear(self, ctx: commands.Context, *args):
        """Clear messages with ID ranges.

        Usage:
        t.clear <message_id> - delete from latest to this message (inclusive)
        t.clear <id1> <id2> - delete messages between two IDs (inclusive)
        t.clear (reply) - delete from latest to replied message
        """
        # Check if user is replying to a message
        replied_msg = None
        if ctx.message.reference and ctx.message.reference.message_id:
            try:
                replied_msg = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
            except (discord.NotFound, discord.HTTPException):
                pass

        # Determine target message IDs
        target_ids: list[int] = []

        if not args:
            if replied_msg:
                target_ids = [replied_msg.id]
            else:
                await ctx.reply(
                    "❌ Vui lòng cung cấp ID tin nhắn hoặc reply tin nhắn muốn xóa."
                )
                return
        elif len(args) == 1:
            try:
                target_ids = [int(args[0])]
            except ValueError:
                await ctx.reply("❌ ID tin nhắn không hợp lệ.")
                return
        elif len(args) >= 2:
            try:
                id1 = int(args[0])
                id2 = int(args[1])
                if id1 > id2:
                    id1, id2 = id2, id1
                target_ids = [id1, id2]
            except ValueError:
                await ctx.reply("❌ ID tin nhắn không hợp lệ.")
                return

        # Determine the range of messages to delete
        if len(target_ids) == 1:
            target_id = target_ids[0]
            # Fetch messages from newest down to target_id inclusive
            messages_to_delete: list[discord.Message] = []
            async for msg in ctx.channel.history(limit=None):
                if msg.id <= target_id:
                    messages_to_delete.append(msg)
                    if msg.id == target_id:
                        break
                else:
                    messages_to_delete.append(msg)
            messages_to_delete.reverse()

        elif len(target_ids) == 2:
            id_start, id_end = target_ids
            # Fetch messages between the two IDs (inclusive)
            messages_to_delete: list[discord.Message] = []
            async for msg in ctx.channel.history(limit=None):
                if id_start <= msg.id <= id_end:
                    messages_to_delete.append(msg)
                elif msg.id < id_start:
                    break
            messages_to_delete.sort(key=lambda m: m.id)

        # If replying without args, adjust the range
        if not args and replied_msg:
            # Delete from latest to replied message inclusive
            messages_to_delete: list[discord.Message] = []
            async for msg in ctx.channel.history(limit=None):
                if msg.id <= replied_msg.id:
                    messages_to_delete.append(msg)
                    if msg.id == replied_msg.id:
                        break
                else:
                    messages_to_delete.append(msg)
            messages_to_delete.reverse()

        # Filter to only messages bot can delete (within 14 days, bot permissions)
        deletable: list[discord.Message] = []
        now = discord.utils.utcnow()
        for msg in messages_to_delete:
            age = (now - msg.created_at).total_seconds()
            if age > 1209600:  # 14 days in seconds
                continue
            deletable.append(msg)

        if not deletable:
            await ctx.reply(
                "❌ Không tìm thấy tin nhắn có thể xóa trong phạm vi cho phép (14 ngày gần đây)."
            )
            return

        # Show confirmation embed
        embed = discord.Embed(
            title="🗑️ Xác nhận xóa tin nhắn",
            color=discord.Color.red(),
            description=f"Sẽ xóa **{len(deletable)}** tin nhắn",
        )

        # Add content snippets
        lines: list[str] = []
        for msg in deletable[:20]:
            content = msg.content or ""
            if len(content) > 100:
                snippet = content[:100] + "..."
            else:
                snippet = content
            author = msg.author.mention if msg.author else "Unknown"
            lines.append(f"**{author}**: {snippet}")
        if len(deletable) > 20:
            lines.append(f"... và {len(deletable) - 20} tin nhắn khác")
        embed.add_field(
            name="Nội dung sẽ xóa",
            value="\n".join(lines)[:1024],
            inline=False,
        )

        # Add range info
        if len(target_ids) == 1:
            embed.add_field(
                name="Khoảng xóa",
                value=f"Từ tin nhắn mới nhất đến tin nhắn ID `{target_ids[0]}`",
                inline=False,
            )
        elif len(target_ids) == 2:
            embed.add_field(
                name="Khoảng xóa",
                value=f"Từ tin nhắn ID `{target_ids[0]}` đến ID `{target_ids[1]}`",
                inline=False,
            )

        confirmation = await ctx.reply(embed=embed, delete_after=3)

        # Delete the messages
        deleted_count = 0
        for msg in deletable:
            try:
                await msg.delete()
                deleted_count += 1
            except (discord.Forbidden, discord.HTTPException):
                pass

        # Update confirmation with result
        result_embed = discord.Embed(
            title="✅ Kết quả",
            color=discord.Color.green()
            if deleted_count == len(deletable)
            else discord.Color.orange(),
            description=f"Đã xóa **{deleted_count}** tin nhắn từ **{len(deletable)}** tìm được.",
        )
        try:
            await confirmation.edit(embed=result_embed)
        except discord.NotFound:
            await ctx.reply(embed=result_embed)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Clear(bot))
