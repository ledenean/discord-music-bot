import nextcord
from nextcord.ext import commands
from nextcord import Interaction
import wavelink 
from wavelink.ext import spotify

intents = nextcord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents)

class ControlPanel(nextcord.ui.View):
    def __init__(self, vc, ctx):
        super().__init__()
        self.vc = vc
        self.ctx = ctx
    
    @nextcord.ui.button(label="Resume/Pause", style=nextcord.ButtonStyle.blurple)
    async def resume_and_pause(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        for child in self.children:
            child.disabled = False

        if self.vc.is_paused():
            await self.vc.resume()
            await interaction.message.edit(content="Resumed", view=self)
        else:
            await self.vc.pause()
            await interaction.message.edit(content="Paused", view=self)

    @nextcord.ui.button(label="Queue", style=nextcord.ButtonStyle.blurple)
    async def queue(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        for child in self.children:
            child.disabled = False

        em = nextcord.Embed(title="Queue")
        queue = self.vc.queue.copy()

        if self.vc.queue.is_empty:
            button.disabled = True
            em.add_field(name="Queue", value="No more songs in queue")
        
        songCount = 0
        for song in queue:
            songCount += 1
            em.add_field(name=f"Track Num {str(songCount)}", value=f"`{song.title}`", inline=False)
        await interaction.message.edit(embed=em, view=self)

    @nextcord.ui.button(label="Skip", style=nextcord.ButtonStyle.blurple)
    async def skip(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        for child in self.children:
            child.disabled = False
        
        if not self.vc.queue.is_empty:
            await self.vc.stop()
        else:
            await self.vc.disconnect()

    @nextcord.ui.button(label="Disconnect", style=nextcord.ButtonStyle.red)
    async def disconnect(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        for child in self.children:
            child.disabled = True

        await self.vc.disconnect()
        await interaction.message.edit(content="Disconnect", view=self) 

@bot.event
async def on_ready():
    print("Bot is ready!")
    bot.loop.create_task(node_connect())

@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f"Node {node.identifier} is ready!")

async def node_connect():
    await bot.wait_until_ready()
    await wavelink.NodePool.create_node(bot=bot, host='host', port=443, password='1234', https=True, spotify_client=spotify.SpotifyClient(client_id="client ID", client_secret="client secret"))

@bot.event
async def on_wavelink_track_end(player: wavelink.Player, track: wavelink.Track, reason):
    ctx = player.ctx
    vc: player = ctx.voice_client
    
    view = ControlPanel(vc, ctx)
    em = nextcord.Embed(title="Playing")

    if not vc.queue.is_empty:
        nextSong = await vc.queue.get_wait()
        await vc.play(nextSong)
        em.add_field(name='Title', value=f'{nextSong.title}')
        await ctx.send(embed=em, view=view)
    else:
        await vc.disconnect()

@bot.command()
async def play(ctx: commands.Context, *, search: str):
    if not ctx.voice_client:
        vc: wavelink.Player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
    elif not getattr(ctx.author.voice, "channel", None):
        return await ctx.send("Join voice channel first")
    else:
        vc: wavelink.Player = ctx.voice_client

    track = await spotify.SpotifyTrack.search(query=search, return_first=True)    
    view = ControlPanel(vc, ctx)
    em = nextcord.Embed(title="Playing")
    if vc.queue.is_empty and not vc.is_playing():
        await vc.play(track)
        em.add_field(name='Title', value=f'{track.title}')
    else:
        await vc.queue.put_wait(track)
        em.add_field(name="Queue", value=f'Added `{track.title}` to the queue')
    
    await ctx.send(embed=em, view=view)

    vc.ctx = ctx
    setattr(vc, "loop", False)
    
    
@bot.command()
async def pause(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    
    await vc.pause()
    await ctx.send("Paused")

@bot.command()
async def resume(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    
    await vc.resume()
    await ctx.send("Resuming")

@bot.command()
async def stop(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    
    await vc.stop()
    await ctx.send("Stopped the music")

@bot.command()
async def disconnect(ctx: commands.Context):
    vc: wavelink.Player = ctx.voice_client
    
    await vc.disconnect()
    await ctx.send("Bye!")


bot.run("token")