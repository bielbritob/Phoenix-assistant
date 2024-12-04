import discord
from discord.ext import commands
import speech_recognition as sr
from keras.models import load_model
import numpy as np
import cv2
import asyncio
import pygame
import queue
import threading
import json


command_queue = queue.Queue()

ponto_queue = queue.Queue(2)

game_loop = None # Controle das leds, variavel global

foi_chamado = None # Variavel se entendeu um comando

entendeu = None

text = None # Texto reconhecido do recognizer


# Vars globais do "enviar tarefa"
comando = None
paginas = None
conteudo = None
quando = None
materia = None

def run_phoenix():
    global command_queue, game_loop, foi_chamado, comando, paginas, conteudo, quando, materia  # Simulação do queue

    class Animation:
        """Classe de animação para gerenciar quadros e transições."""

        def __init__(self, frames, frame_duration, repeat_count=0, duration=None, delay=0):
            self.frames = frames
            self.frame_duration = frame_duration
            self.current_frame = 0
            self.time_passed = 0
            self.repeats = 0
            self.max_repeats = repeat_count
            self.duration = duration
            self.time_played = 0
            self.delay = delay
            self.time_since_last_animation = 0
            self.animation_finished = False

        def reset(self):
            """Reinicia a animação."""
            self.current_frame = 0
            self.time_passed = 0
            self.repeats = 0
            self.time_played = 0
            self.animation_finished = False
            self.time_since_last_animation = 0

        def update(self, dt):
            """Atualiza a animação conforme o tempo passado."""
            if self.animation_finished:
                return False
            self.time_since_last_animation += dt
            if self.time_since_last_animation < self.delay:
                return True
            self.time_passed += dt
            if self.time_passed >= self.frame_duration:
                self.time_passed = 0
                self.current_frame += 1
                if self.current_frame >= len(self.frames):
                    self.current_frame = 0
                    self.repeats += 1
                    self.time_since_last_animation = 0
                    if self.max_repeats and self.repeats >= self.max_repeats:
                        self.animation_finished = True
                        return False
            if self.duration:
                self.time_played += dt
                if self.time_played >= self.duration:
                    self.animation_finished = True
                    return False
            return True

        def get_current_frame(self):
            return self.frames[self.current_frame]

    class CaixaDeDialogo:
        """Classe para desenhar e gerenciar a caixa de diálogo."""

        def __init__(self, set_screen, font_path=None, name_font_path=None):
            self.screen = set_screen
            # Use a fonte personalizada ou a fonte padrão
            self.font = pygame.font.Font(font_path, 35)
            self.name_font = pygame.font.Font(name_font_path, 40)
            self.dialogue_color = (50, 50, 50)
            self.name_bar_color = (30, 30, 30)
            self.white = (255, 255, 255)
            self.black = (0, 0, 0)

        @staticmethod
        def wrap_text(text, font, max_width):
            words = text.split(' ')
            lines = []
            current_line = ""
            for word in words:
                if font.size(current_line + word)[0] < max_width:
                    current_line += word + " "
                else:
                    lines.append(current_line)
                    current_line = word + " "
            lines.append(current_line)
            return lines

        def draw(self, text, character_name="Fenix"):
            dialogue_box_rect = pygame.Rect(370, 500, 850, 150)
            name_bar_rect = pygame.Rect(370, 460, 300, 40)
            pygame.draw.rect(self.screen, self.dialogue_color, dialogue_box_rect, border_radius=10)
            pygame.draw.rect(self.screen, self.name_bar_color, name_bar_rect, border_radius=10)
            pygame.draw.rect(self.screen, self.black, dialogue_box_rect, 5, border_radius=10)
            pygame.draw.rect(self.screen, self.black, name_bar_rect, 5, border_radius=10)
            name_text = self.name_font.render(character_name, True, self.white)
            self.screen.blit(name_text, (390, 467))
            lines = self.wrap_text(text, self.font, 830)
            y_offset = 520
            x_offset = 390
            for line in lines:
                rendered_line = self.font.render(line, True, self.white)
                self.screen.blit(rendered_line, (x_offset, y_offset))
                y_offset += 40

    class Fenix:
        """Classe principal do personagem Fênix."""

        def __init__(self, set_screen, set_command_queue):
            self.screen = set_screen
            self.command_queue = set_command_queue
            self.animations = self.load_animations()
            self.current_animation = self.animations["idle"]
            self.texto_recebido = ""
            self.dialogue_box = CaixaDeDialogo(screen, None,  None)
            self.blink_animation = self.animations["blink"]
            self.thinking_active = False
            self.animation_synchronized = False

        def load_animations(self):
            """Carrega as animações."""
            return {
                "active": Animation([self.load_image("assets/active.png")], 100),
                "blink": Animation([self.load_image(f"assets/blink_{i}.png") for i in range(4)], 200,
                                   delay=4000),
                "nod": Animation([self.load_image(f"assets/nod_{i}.png") for i in range(3)], 300,
                                 repeat_count=2),
                "headshake": Animation([self.load_image(f"assets/headshake_{i}.png") for i in range(3)],
                                       300, repeat_count=2),
                "thinking": Animation(
                    [self.load_image(f'assets/thinkingbody_{i}.png') for i in range(3)], 250,
                    duration=3000),
                "idle": Animation([self.load_image("assets/idle.png")], 100),
                "talking": Animation([self.load_image(f"assets/talking_{i}.png") for i in range(4)],
                                     100),
                "embashed": Animation([self.load_image(f"assets/abashed.png")], 100),
                "embashed_talking": Animation(
                    [self.load_image(f"assets/abashedtalk_{i}.png") for i in range(4)], 200),
            }

        @staticmethod
        def load_image(path):
            image = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(image, (800, 500))

        def set_current_animation(self, animation):
            self.current_animation = self.animations.get(animation, self.animations["idle"])
            self.current_animation.reset()

        def update_animation(self, dt):
            if self.current_animation:
                self.animation_synchronized = self.current_animation.update(dt)

        def draw_character(self):
            frame = self.current_animation.get_current_frame()
            self.screen.blit(frame, (850 - 800 // 2, 390 - 500 // 2))

        def handle_commands(self):
            if self.command_queue is not None and not self.command_queue.empty():
                command, texto_recebido = self.command_queue.get()
                self.texto_recebido = texto_recebido if texto_recebido else "[...]"
                self.set_current_animation(command)
                if command == "thinking":
                    self.thinking_active = True
                else:
                    self.thinking_active = False

        def draw_dialogue(self):
            if self.animation_synchronized:
                self.dialogue_box.draw(self.texto_recebido)

    class GameLoop:
        """Classe que gerencia o loop principal do jogo."""

        def __init__(self, set_fenix):
            self.fenix = set_fenix
            self.running = True
            self.clock = pygame.time.Clock()
            self.points_thread = None
            self.running_thread = True  # Variável de controle para a thread
            self.led_webcam = False
            self.led_pitoco = False
            self.led_discord = False
            self.led_fenix = False

        def pontos(self, soPensarbool=False,mostrar_pensandobool=False, ativar_customanim=False, numeros=1, anim="blink",text=None, delay1=0, delay2=0):

            def mostrar_pensando():
                for _ in range(numeros):
                    pygame.time.delay(550)
                    command_queue.put(('thinking', '[.  ]'))
                    pygame.time.delay(550)
                    command_queue.put(('thinking', '[.. ]'))
                    pygame.time.delay(550)
                    command_queue.put(('thinking', '[...]'))

            def soPensar():
                pygame.time.delay(550)
                command_queue.put(('nod', 'Enviando.'))
                pygame.time.delay(550)
                command_queue.put(('blink', 'Enviando..'))
                pygame.time.delay(550)
                command_queue.put(('blink', 'Enviando...'))

            def customanim():
                pygame.time.delay(delay1)
                command_queue.put((anim, text))
                pygame.time.delay(delay2)

            if mostrar_pensandobool:
                mostrar_pensando()

            if soPensarbool:
                soPensar()

            if ativar_customanim:
                customanim()




        def ligar_web(self):
            self.led_webcam = True
        def ligar_pitoco(self):
            self.led_pitoco = True
        def desligar_pitoco(self):
            self.led_pitoco = False
        def ligar_discord(self):
            self.led_discord = True
        def ligar_fenix(self):
            self.led_fenix = True


        def run(self):
            # Dimensões da janela
            WINDOW_WIDTH = 1500
            WINDOW_HEIGHT = 700

            # Cores
            WHITE = (255, 255, 255)
            BLACK = (0, 0, 0)

            # Carregar os 13 frames da animação de fundo
            background_frames = [pygame.image.load(f'assets/fundofinal{i}.png').convert_alpha() for i in range(13)]
            background_frame_duration = 100  # Duração de cada frame em milissegundos
            current_background_frame = 0
            background_time_elapsed = 0

            # Carrega a imagem da barra de título
            titlebar_img = pygame.image.load('assets/titlebarIdle.png')

            # Carrega backgrond phoenix
            backgrond_phoenix = pygame.image.load('assets/testefundo.png')

            # Carrega x da titlebar
            x_titlebar = pygame.image.load('assets/x_titlebar.png')

            # Carrega Leds off's
            led_webcam_off = pygame.image.load('assets/led_webc.png')
            led_pitoco_off = pygame.image.load('assets/led_pitoco.png')
            led_discord_off = pygame.image.load('assets/led_discord.png')
            led_fenix_off = pygame.image.load('assets/led_fenix.png')

            # Carrega Leds on's
            led_webcam_on = pygame.image.load('assets/led_webc_on.png')
            led_pitoco_on = pygame.image.load('assets/led_pitoco_on.png')
            led_discord_on = pygame.image.load('assets/led_discord_on.png')
            led_fenix_on = pygame.image.load('assets/led_fenix_on.png')


            # Define o retângulo do botão de fechar
            close_button_rect = pygame.Rect(WINDOW_WIDTH - 39, 0, 37, 39)  # Exemplo de posição e tamanho

            while self.running:
                mouse_pos = pygame.mouse.get_pos()
                dt = self.clock.tick(60)

                # Atualizar o frame do background com base no tempo decorrido
                background_time_elapsed += dt
                if background_time_elapsed >= background_frame_duration:
                    background_time_elapsed = 0
                    current_background_frame = (current_background_frame + 1) % len(background_frames)

                # Desenhar o frame atual do background
                screen.blit(background_frames[current_background_frame], (0, 0))

                self.fenix.update_animation(dt)
                self.fenix.handle_commands()
                self.fenix.draw_character()
                self.fenix.draw_dialogue()  # Só exibe o diálogo sincronizado com a animação

                pygame.draw.rect(screen, (0, 0, 0), close_button_rect)
                screen.blit(titlebar_img, (0, 0))

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if close_button_rect.collidepoint(event.pos):
                            self.running = False
                            
                    # aq era o q e e

                # Verifica a fila ponto_queue sem bloquear o loop
                try:
                    result_ponto_q = ponto_queue.get_nowait()
                    if result_ponto_q:
                        # Liga a thread de pontos se ainda não estiver ativa
                        if not self.running_thread:
                            self.running_thread = True
                            self.points_thread = threading.Thread(target=self.pontos)
                            self.points_thread.daemon = True
                            self.points_thread.start()
                    else:
                        # Desliga a thread de pontos
                        self.running_thread = False
                        if self.points_thread is not None:
                            self.points_thread.join()
                        #command_queue.put(('blink', '[...]'))
                except queue.Empty:
                    # Se a fila está vazia, continua normalmente
                    pass


                # logica leds on/off
                if self.led_webcam == False:
                    screen.blit(led_webcam_off)
                else:
                    screen.blit(led_webcam_on)

                if self.led_pitoco == False:
                    screen.blit(led_pitoco_off)
                else:
                    screen.blit(led_pitoco_on)

                if self.led_discord == False:
                    screen.blit(led_discord_off)
                else:
                    screen.blit(led_discord_on)

                if self.led_fenix == False:
                    screen.blit(led_fenix_off)
                else:
                    screen.blit(led_fenix_on)

                if close_button_rect.collidepoint(mouse_pos):
                    screen.blit(x_titlebar)

                pygame.display.flip()


    # load moscaascii
    moscaico = pygame.image.load('assets/moscaascii256x.png')

    pygame.display.set_icon(moscaico)

    # Inicializa o pygame e roda o jogo
    pygame.init()


    # Dimensões da janela
    WINDOW_WIDTH = 1500
    WINDOW_HEIGHT = 700
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)
    pygame.display.set_caption('Phoenix')
    fenix = Fenix(screen, command_queue)
    game_loop = GameLoop(fenix)


    # Adiciona comandos na fila (ação, texto)
    command_queue.put(("idle", "Iniciando..."))
    game_loop.ligar_fenix()




    game_loop.run()
    pygame.quit()

################################################################################
TOKEN = open('data/discordToken', 'r').read()


# Abrir e ler o arquivo JSON
with open('data/discordChannels', 'r') as file:
    canais = json.load(file)  # Carrega o conteúdo do JSON como um dicionário

#################################################################################




def run_discord_bot():
    global game_loop
    intents = discord.Intents.default()
    intents.typing = False
    intents.presences = True
    intents.message_content = True

    bot = commands.Bot(command_prefix='!', intents=intents)


    @bot.event
    async def on_ready():
        print(f'{bot.user.name} está online!')
        if game_loop is not None:
            game_loop.ligar_discord()

        print("""
        
        ______  _   _  _____  _____  _   _  _____ __   __
        | ___ \| | | ||  _  ||  ___|| \ | ||_   _|\ \ / /
        | |_/ /| |_| || | | || |__  |  \| |  | |   \ V / 
        |  __/ |  _  || | | ||  __| | . ` |  | |   /   \ 
        | |    | | | |\ \_/ /| |___ | |\  | _| |_ / /^\ |
        \_|    \_| |_/ \___/ \____/ \_| \_/ \___/ \/   \/
        
        
        
        """)

    @bot.command()
    async def embed(ctx:commands.Context):
        channel = ctx.channel
        embed = discord.Embed(title="Tarefa de Português", color=0x00ff00)
        embed.add_field(name="Páginas:", value="540", inline=False)
        embed.add_field(name="Conteúdo:", value="Analisar os capítulos 5 e 6 do livro \"Dom Casmurro\".", inline=False)
        embed.add_field(name="Prazo:", value="Até sexta-feira", inline=False)
        embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
        await channel.send(embed=embed)


    @bot.command()
    async def limparchat(ctx: commands.Context):
        user = ctx.author.id
        if user == 632367292226994176:
            await ctx.channel.purge(limit=15)
        else:
            await ctx.send('**Vc não é meu dono!**')

    @bot.command()
    async def sync(ctx:commands.Context):
        if ctx.author.id == 632367292226994176:
            server = discord.Object(id=1289701164450840608)
            sincs = await bot.tree.sync(guild=server)
            await ctx.reply(f"{len(sincs)} comandos sync'eds")
        else:
            await ctx.reply("vc nao pode usar isso...")

    @bot.tree.command(description="enviar tarefa para determinado chat")
    async def enviar_tarefa(ctx, materia: str, paginas: str, conteudo: str, quando: str):
        # Concatena o que foi dito após a matéria (páginas ou conteúdo)
        #paginas = ' '.join(args)

        # Verifica se a matéria existe no dicionário
        canal_id = canais.get(materia.lower())
        print(canais, canal_id)
        if canal_id:
            canal = bot.get_channel(canal_id)
            print(canal)
            if canal:
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:", value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}",inline=False)
                embed.add_field(name="Prazo:",value=f"{quando.capitalize()}",inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await canal.send(embed=embed)
                #await canal.send(f"Tarefa de {materia.capitalize()}: {paginas}")
                #await ctx.send(f"Tarefa de {materia.capitalize()} enviada no canal.")
            else:
                await ctx.send("Erro ao encontrar o canal. Verifique o ID.")
        else:
            await ctx.send("Matéria não encontrada!")


    bot.run(TOKEN)


# Função do Pitoco
def pitoco_commands():
    global game_loop, entendeu, text  # Acessa a variável global game_loop
    if game_loop is not None:
        game_loop.ligar_pitoco()
    def recognize_speech():
        global entendeu, text, game_loop
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("Ouvindo...")

            game_loop.pontos(anim="blink",text="Ouvindo...", ativar_customanim=True, delay1=0,delay2=0)

            ponto_queue.put(True)
            r.adjust_for_ambient_noise(source)
            audio = r.listen(source)
            ponto_queue.put(False)
            game_loop.pontos(mostrar_pensandobool=True, numeros=2, delay1=0)
            try:
                text = r.recognize_google(audio, language='pt-br')
                print(f"Você disse: {text}")
                game_loop.pontos(anim="talking", text=f"você disse: {text}", ativar_customanim=True, delay1=0, delay2=2000)
                #speak(f'você disse {text}')
                #speak(audio)

                if text == "Reiniciar":
                    enviar_tarefa()

                return text.lower()

            except:
                print("Não entendi...")
                game_loop.pontos(anim="headshake", text="Não entendi...", ativar_customanim=True, delay1=0,delay2=1500)
                entendeu = False
                return ""


    # Fluxo de Conversa
    def enviar_tarefa():
        global entendeu, comando, paginas, conteudo, quando, materia, foi_chamado
        # prefixo sempre in letter case
        prefixo = recognize_speech()
        if "fênix" in prefixo:
            foi_chamado = True
            game_loop.pontos(anim="embashed_talking", text="Oi, me chamou. O que deseja?", ativar_customanim=True, delay1=0,delay2=1000)
            game_loop.pontos(delay1=1000,delay2=2000,anim="embashed", text="Oi, me chamou. O que deseja?", ativar_customanim=True)
            #speak("Oi, me chamou. O que deseja?")
            comando = recognize_speech()
            foi_chamado = False

            if "enviar tarefa" in comando:
                game_loop.pontos(anim="talking", text="De qual matéria?", ativar_customanim=True, delay1=0,delay2=800)
                game_loop.pontos(anim="blink", text="De qual matéria?", ativar_customanim=True, delay1=1000, delay2=2000)
                #speak("De qual matéria?")
                materia = recognize_speech()
                print(f"[{materia}]")
                if materia == "":
                    game_loop.pontos(anim="headshake", text="Fale novamente a matéria", ativar_customanim=True, delay1=0,delay2=1000)
                    game_loop.pontos(anim="talking", text="Fale novamente a matéria", ativar_customanim=True, delay1=500,delay2=800)
                    game_loop.pontos(anim="blink", text="Fale novamente a matéria", ativar_customanim=True, delay1=500,delay2=2000)
                    #speak("Fale novamente a matéria")
                    materia = recognize_speech()

                game_loop.pontos(anim="talking", text="Quais páginas?", ativar_customanim=True, delay1=0, delay2=1000)
                game_loop.pontos(anim="blink", text="Quais páginas?", ativar_customanim=True, delay1=1000,delay2=2000)
                #speak("Quais páginas?")
                paginas = recognize_speech()
                print(f"paginas: [{paginas}]")
                if paginas == "":
                    game_loop.pontos(anim="headshake", text="Fale novamente as páginas", ativar_customanim=True, delay1=0,delay2=1000)
                    game_loop.pontos(anim="talking", text="Fale novamente as páginas", ativar_customanim=True, delay1=500,delay2=800)
                    game_loop.pontos(anim="blink", text="Fale novamente as páginas", ativar_customanim=True, delay1=1000,delay2=2000)
                    #speak("Fale novamente as paginas")
                    paginas = recognize_speech()

                game_loop.pontos(anim="talking", text="Qual conteúdo?", ativar_customanim=True, delay1=0, delay2=800)
                game_loop.pontos(anim="blink", text="Qual conteúdo?", ativar_customanim=True, delay1=1000, delay2=2000)
                #speak("Qual conteúdo?")
                conteudo = recognize_speech()
                print(f"conteudo: [{conteudo}]")
                if conteudo == "":
                    game_loop.pontos(anim="headshake", text="Fale novamente o conteúdo", ativar_customanim=True, delay1=0,delay2=1000)
                    game_loop.pontos(anim="talking", text="Fale novamente o conteúdo", ativar_customanim=True, delay1=500,delay2=800)
                    game_loop.pontos(anim="blink", text="Fale novamente o conteúdo", ativar_customanim=True, delay1=1000,delay2=2000)
                    #speak("Fale novamente o conteúdo")
                    conteudo = recognize_speech()


                game_loop.pontos(anim="talking", text="Tem prazo de entrega?", ativar_customanim=True, delay1=0,delay2=800)
                game_loop.pontos(anim="blink", text="Tem prazo de entrega?", ativar_customanim=True, delay1=1000,delay2=2000)
                #speak("Tem prazo de entrega?")

                prazo = recognize_speech()
                print(f"prazo = {prazo}")
                quando = prazo


                ###########################################################

                game_loop.pontos(anim="talking",
                                 text="Enviando...",
                                 ativar_customanim=True, delay1=0, delay2=800)
                game_loop.pontos(soPensarbool=True)
                # Envia tarefa para o Discord
                asyncio.run(send_task_to_discord(materia, paginas, conteudo, quando))

                if materia == canais:
                    game_loop.pontos(anim="talking", text=f"Tarefa de {materia} enviada para o Discord. No chat de {materia}", ativar_customanim=True, delay1=0, delay2=800)
                    game_loop.pontos(anim="blink", text=f"Tarefa de {materia} enviada para o Discord. No chat de {materia}", ativar_customanim=True,delay1=1000, delay2=2000)




                else:
                    game_loop.pontos(anim="talking", text=f"Tarefa de [{materia}] enviada para o Discord.", ativar_customanim=True, delay1=0, delay2=800)
                    game_loop.pontos(anim="blink", text=f"Tarefa de [{materia}] enviada para o Discord.", ativar_customanim=True,delay1=1000, delay2=2000)
                    #speak(f"Tarefa de {materia} enviada para o Discord. No chat geral")
            else:
                game_loop.pontos(anim="headshake", text="Vc disse algo? não entendi...", ativar_customanim=True,delay1=0, delay2=1000)
                game_loop.pontos(anim="talking", text="Vc disse algo? não entendi...", ativar_customanim=True,delay1=500, delay2=800)
                game_loop.pontos(anim="blink", text="Ouvindo...", ativar_customanim=True, delay1=1000, delay2=2000)

        else:
            print(prefixo)
    # Função para enviar a tarefa no Discord
    async def send_task_to_discord(materia, paginas, conteudo, quando):
        intents = discord.Intents.default()
        bot = commands.Bot(command_prefix="!", intents=intents)


        @bot.event
        async def on_ready():
            channel_geral = bot.get_channel(1289715562737438802)
            channel_mat = bot.get_channel(1289981058720469173)
            channel_bio = bot.get_channel(1291092585028255745)
            channel_fisica = bot.get_channel(1291092526618378303)
            channel_quimica = bot.get_channel(1291092545388019825)
            channel_ingles = bot.get_channel(1291092584202244136)
            channel_historia = bot.get_channel(1291092693790756897)
            channel_geografia = bot.get_channel(1291092833331318855)
            channel_port = bot.get_channel(1289995044056731709)
            channel_arg = bot.get_channel(1291092742276907070)
            channel_test = bot.get_channel(1304165249095700491)

            if materia == "matemática":
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_mat.send(embed=embed)
                #await channel_mat.send(f"# Tarefa de {materia}:\n páginas: {paginas}")

            elif materia == "português":
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_port.send(embed=embed)
                #await channel_port.send(f"Tarefa de {materia}:\n páginas: {paginas}")

            elif materia == 'biologia':
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_bio.send(embed=embed)
                #await channel_bio.send(f"Tarefa de {materia}:\n páginas: {paginas}")

            elif materia == 'física':
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_fisica.send(embed=embed)
                await channel_fisica.send(f"Tarefa de {materia}:\n páginas: {paginas}")

            elif materia == 'geografia':
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_geografia.send(embed=embed)
                await channel_geografia.send(f"Tarefa de {materia}:\n páginas: {paginas}")

            elif materia == 'quimica':
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_quimica.send(embed=embed)
                #await channel_quimica.send(f"Tarefa de {materia}:\n páginas: {paginas}")

            elif materia == 'inglês':
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_ingles.send(embed=embed)
                #await channel_ingles.send(f"Tarefa de {materia}:\n# páginas: {paginas}")

            elif materia == 'história':
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_historia.send(embed=embed)
                #await channel_historia.send(f"Tarefa de {materia}:\n páginas: {paginas}")

            elif materia == 'argumentação':
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_arg.send(embed=embed)
                #await channel_arg.send(f"Tarefa de {materia}:\n páginas: {paginas}")

            elif materia == 'teste':
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_test.send(embed=embed)
                #await channel_arg.send(f"Tarefa de {materia}:\n páginas: {paginas}")

            else:
                print('ELSE!')
                embed = discord.Embed(title=f"Tarefa de **{materia.capitalize()}**", color=0x00ff00)
                embed.add_field(name="Páginas:",value=f"{paginas.capitalize()}",inline=False)
                embed.add_field(name="Conteúdo:",value=f"{conteudo.capitalize()}", inline=False)
                embed.add_field(name="Prazo:", value=f"{quando.capitalize()}", inline=False)
                embed.set_footer(icon_url="https://cdn.discordapp.com/attachments/1284917057808498728/1291135161823399976/mosca2sfundo.png?ex=66fefed2&is=66fdad52&hm=22a5103bcbdcfa5cf03dcad65ef450cbd23d925335599290962e81b2bc8ca873&",text="Mosca - 2024")
                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1284917057808498728/1291134739721355334/moscasfundo.png?ex=66fefe6e&is=66fdacee&hm=d71de3b5f2aea2ccb270e6470966ab9058f4533e69dec3c998e1b19872b6c8ac&")
                await channel_geral.send(embed=embed)
                #await channel_geral.send(f"# Tarefa de [{materia}] nao tinha chat especifico feito. entao enviei aq msm >> Pagina: [{paginas}]")
            await bot.close()

        await bot.start(TOKEN)

    enviar_tarefa()


# Função da câmera
def verify_webcam():
    global game_loop  # Acessa a variável global game_loop
    np.set_printoptions(suppress=True)
    camera = cv2.VideoCapture(0)
    model = load_model("keras_model.h5", compile=False)
    class_names = open("labels.txt", "r").readlines()

    while True:
        ret, image = camera.read()
        image_resized = cv2.resize(image, (224, 224), interpolation=cv2.INTER_AREA)
        image_array = np.asarray(image_resized, dtype=np.float32).reshape(1, 224, 224, 3)
        image_array = (image_array / 127.5) - 1
        prediction = model.predict(image_array)
        index = np.argmax(prediction)
        class_name = class_names[index].strip()
        confidence_score = prediction[0][index]
        print('\033[1:32mWEBCAM LiGADA\033[m')
        if game_loop is not None:
            game_loop.ligar_web()

        janela = False

        if janela != False:
            print("Class:", class_name, "Confidence Score:", str(np.round(confidence_score * 100))[:-2], "%")
            cv2.putText(image, f"{class_name} ({np.round(confidence_score * 100)}%)", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 0), 3, cv2.LINE_AA)
            windowname = 'Webcam Image'
            cv2.imshow(windowname, image)

            if cv2.waitKey(1) == 27 or cv2.getWindowProperty(windowname, cv2.WND_PROP_VISIBLE) < 1:
                break

            camera.release()
            cv2.destroyAllWindows()

        if class_name == '0 biel':
            pitoco_commands()  # Chama o Pitoco quando detecta você
        else:
            game_loop.desligar_pitoco()
            game_loop.pontos(anim="idle", text="Biel fora da camera...",ativar_customanim=True, delay1=500, delay2=1000)
            print('Nada')


# Iniciar a thread do bot
discord_bot_thread = threading.Thread(target=run_discord_bot)
discord_bot_thread.daemon = True
discord_bot_thread.start()

phoenix_thread = threading.Thread(target=run_phoenix)
phoenix_thread.daemon = True
phoenix_thread.start()

# Rodar a função da câmera
verify_webcam()

###############################################################################################################



