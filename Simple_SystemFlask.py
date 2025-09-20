#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

import sys
import os
import time
import threading
import json
import httplib
import ssl
import socket
import subprocess
import codecs
from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
from Queue import Queue, Empty

# Configurar stdout para UTF-8
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

# Importar NAOqi
try:
    from naoqi import ALProxy, ALModule, ALBroker
    HAS_NAOQI = True
    print("NAOqi SDK encontrado!" )
except ImportError:
    HAS_NAOQI = False
    print("NAOqi SDK nao encontrado - funcionara em modo simulacao")

def safe_str(value):
    """Converter qualquer valor para string UTF-8 segura"""
    if isinstance(value, unicode):
        return value.encode('utf-8', 'replace')
    elif isinstance(value, str):
        try:
            return value.decode('utf-8').encode('utf-8')
        except:
            return value
    else:
        return str(value)

def limpar_texto_para_processamento(texto):
    """Remove acentos e caracteres especiais para processamento interno"""
    if isinstance(texto, unicode):
        texto_str = texto.encode('utf-8')
    else:
        texto_str = str(texto)
    
    # Conversões básicas para processamento
    substituicoes = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u',
        'ç': 'c'
    }
    
    try:
        if isinstance(texto_str, str):
            texto_str = texto_str.decode('utf-8')
        
        for acentuado, sem_acento in substituicoes.items():
            texto_str = texto_str.replace(acentuado, sem_acento)
        
        return texto_str.lower().strip()
    except:
        return str(texto).lower().strip()

app = Flask(__name__)

def get_nao_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# Detectar IP automaticamente
NAO_IP = get_nao_ip()

# Configurações globais
config = {
    "openai_api_key": "AQUI_VAI_SUA_CHAVE_DA_API_OPENAI",
    "nao_ip": NAO_IP,
    "nao_port": 9559,
    "language": "Brazilian",
    "confidence_threshold": 0.50,  # Aumentado para ser menos sensível
    "flask_host": "0.0.0.0",
    "flask_port": 5000,
    "auto_start_voice": True,
    "auto_connect_ai": True
}

# Armazenamento de dados em memória
storage = {
    "vocabulary": [
        "ola", "oi", "tudo bem", "como vai", "bom dia", "boa tarde", "boa noite",
        "qual seu nome", "tchau", "ate logo", "adeus", "pare", "parar",
        "sim", "nao", "talvez", "claro", "certo", "ok", "legal", "bom", "ruim",
        "obrigado", "por favor", "desculpa",
        "levante", "em pe", "sente", "sentar", "deite", "deitar", "relaxe",
        "dance", "dancar", "acenar", "gesto",
        "bateria", "energia", "status", "repetir",
        "porque", "quando", "onde", "como", "qual", "conte", "fale", "explique",
        "futebol", "flamengo", "vasco", "botafogo", "fluminense",
        "robot", "robo", "nao", "inteligencia", "artificial", "tecnologia",
        "oi como voce esta", "como voce esta", "qual o seu nome", "me diga uma piada",
        "me conte uma historia", "qual a sua cor favorita", "voce gosta de musica",
        "voce gosta de dançar", "qual o seu time de futebol", "me fale sobre o brasil",
        "me fale sobre o mundo", "o que voce sabe fazer", "voce pode me ajudar",
        "voce pode dançar", "voce pode cantar", "voce pode contar uma historia",
        "voce pode contar uma piada", "qual a sua comida favorita", "qual a sua musica favorita",
        "qual a sua bebida favorita", "qual o seu filme favorito", "qual o seu livro favorito",
        "qual a sua serie favorita", "qual a sua banda favorita", "qual o seu cantor favorito",
        "qual a sua atriz favorita", "qual o seu ator favorito", "qual a sua flor favorita",
        "qual o seu animal favorito", "qual o seu esporte favorito", "qual a sua cidade favorita",
        "qual o seu pais favorito", "qual a sua viagem favorita", "qual o seu sonho",
        "qual o seu objetivo", "qual a sua missao", "qual a sua visao", "qual o seu valor",
        "qual a sua filosofia", "qual a sua religiao", "qual a sua crença", "qual a sua cultura",
        "qual a sua etnia", "qual a sua nacionalidade", "qual a sua identidade", "qual a sua personalidade",
        "qual a sua historia", "qual a sua experiencia", "qual a sua opiniao", "qual a sua ideia",
        "qual a sua sugestao", "qual a sua recomendacao", "qual a sua critica", "qual a sua avaliacao",
        "qual a sua perspectiva", "qual a sua visao de mundo", "qual a sua visao de futuro",
        "qual a sua visao de vida", "qual a sua visao de sucesso", "qual a sua visao de felicidade",
        "qual a sua visao de amor", "qual a sua visao de amizade", "qual a sua visao de familia",
        "qual a sua visao de trabalho", "qual a sua visao de carreira", "qual a sua visao de dinheiro",
        "qual a sua visao de poder", "qual a sua visao de politica", "qual a sua visao de sociedade",
        "qual a sua visao de mundo", "qual a sua visao de futuro", "qual a sua visao de vida",
        "qual a sua visao de sucesso", "qual a sua visao de felicidade", "qual a sua visao de amor",
        "qual a sua visao de amizade", "qual a sua visao de familia", "qual a sua visao de trabalho",
        "qual a sua visao de carreira", "qual a sua visao de dinheiro", "qual a sua visao de poder",
        "qual a sua visao de politica", "qual a sua visao de sociedade",
        "o que voce acha do brasil", "o que voce acha do mundo", "o que voce acha da inteligencia artificial",
        "o que voce acha da tecnologia", "o que voce acha dos humanos", "o que voce acha dos robos",
        "o que voce acha da vida", "o que voce acha do amor", "o que voce acha da amizade",
        "o que voce acha da familia", "o que voce acha do trabalho", "o que voce acha da carreira",
        "o que voce acha do dinheiro", "o que voce acha do poder", "o que voce acha da politica",
        "o que voce acha da sociedade", "o que voce acha do futuro", "o que voce acha da vida",
        "o que voce acha do sucesso", "o que voce acha da felicidade", "o que voce acha do amor",
        "o que voce acha da amizade", "o que voce acha da familia", "o que voce acha do trabalho",
        "o que voce acha da carreira", "o que voce acha do dinheiro", "o que voce acha do poder",
        "o que voce acha da politica", "o que voce acha da sociedade", "o que voce acha do futuro",
        "o que voce acha da vida", "o que voce acha do sucesso", "o que voce acha da felicidade", "o que voce acha do amor",
        "o que voce acha da amizade", "o que voce acha da familia", "o que voce acha do trabalho", "o que voce acha da carreira", "o que voce acha do dinheiro", "o que voce acha do poder",
        "o que voce acha da politica", "o que voce acha da sociedade", "o que voce acha do futuro",
        "me fale sobre o brasil", "me fale sobre o mundo", "me fale sobre a inteligencia artificial",
        "me fale sobre a tecnologia", "me fale sobre os humanos", "me fale sobre os robos",
        "me fale sobre a vida", "me fale sobre o amor", "me fale sobre a amizade",
        "me fale sobre a familia", "me fale sobre o trabalho", "me fale sobre a carreira",
        "me fale sobre o dinheiro", "me fale sobre o poder", "me fale sobre a politica",
        "me fale sobre a sociedade", "me fale sobre o futuro", "me fale sobre a vida",
        "me fale sobre o sucesso", "me fale sobre a felicidade", "me fale sobre o amor",
        "me fale sobre a amizade", "me fale sobre a familia", "me fale sobre o trabalho",
        "me fale sobre a carreira", "me fale sobre o dinheiro", "me fale sobre o poder",
        "me fale sobre a politica", "me fale sobre a sociedade", "me fale sobre o futuro",
        "me fale sobre a vida", "me fale sobre o sucesso", "me fale sobre a felicidade", "me fale sobre o amor",
        "me fale sobre a amizade", "me fale sobre a familia", "me fale sobre o trabalho", "me fale sobre a carreira", "me fale sobre o dinheiro", "me fale sobre o poder", 
        "me fale sobre a politica", "me fale sobre a sociedade", "me fale sobre o futuro",
        "me fale sobre universo", "me fale sobre ciencia", "me fale sobre historia", "me fale sobre geografia", "me fale sobre arte", "me fale sobre musica", "me fale sobre literatura", "me fale sobre filosofia",
        "me fale sobre religiao", "me fale sobre espiritualidade", "me fale sobre cultura", "me fale sobre etnia", "me fale sobre diversidade", "me fale sobre inclusao", "me fale sobre igualdade", "me fale sobre direitos humanos",
        "me fale sobre democracia", "me fale sobre cidadania", "me fale sobre sustentabilidade", "me fale sobre meio ambiente", "me fale sobre ecologia", "me fale sobre natureza", "me fale sobre animais", "me fale sobre plantas",
        "me fale sobre universo", "me fale sobre ciencia", "me fale sobre historia", "me fale sobre geografia", "me fale sobre arte", "me fale sobre musica", "me fale sobre literatura", "me fale sobre filosofia",
        "me fale sobre religiao", "me fale sobre espiritualidade", "me fale sobre cultura", "me fale sobre etnia", "me fale sobre diversidade", "me fale sobre inclusao", "me fale sobre igualdade", "me fale sobre direitos humanos",
        "me fale sobre democracia", "me fale sobre cidadania", "me fale sobre sustentabilidade", "me fale sobre meio ambiente", "me fale sobre ecologia", "me fale sobre natureza", "me fale sobre animais", "me fale sobre plantas",
        "me explique o que e inteligencia artificial", "me explique o que e machine learning", "me explique o que e deep learning", "me explique o que e redes neurais", "me explique o que e processamento de linguagem natural",  "me explique o que e visao computacional",
        "me explique o que e robótica", "me explique o que e automação", "me explique o que e internet das coisas", "me explique o que e big data", "me explique o que e computação em nuvem", "me explique o que e cibersegurança", "me explique o que e blockchain", "me explique o que e criptomoedas",
        "me explique o que e realidade aumentada", "me explique o que e realidade virtual", "me explique o que e metaverso", "me explique o que e 5g", "me explique o que e computação quântica", "me explique o que e tecnologia 3d",
        "me explique o que e impressao 3d", "me explique o que e biotecnologia", "me explique o que e nanotecnologia", "me explique o que e energia renovavel", "me explique o que e sustentabilidade", "me explique o que e economia circular",
        "me explique o que e desenvolvimento sustentável", "me explique o que e responsabilidade social", "me explique o que e ética na tecnologia",
        "me explique o que e futuro da tecnologia", "me explique o que e futuro da inteligencia artificial",
        "me explique o que e futuro dos robos", "me explique o que e futuro dos humanos", "me explique o que e futuro do trabalho", "me explique o que e futuro da humanidade", "me explique o que e futuro do planeta",
        "me explique o que e futuro do universo", "me explique o que e futuro da vida", "me explique o que e futuro do amor", "me explique o que e futuro da amizade", "me explique o que e futuro da familia",
        "me explique o que e futuro da sociedade", "me explique o que e futuro da politica", "me explique o que e futuro do dinheiro", "me explique o que e futuro do poder",
        "me explique o que e futuro do sucesso", "me explique o que e futuro da felicidade", "me explique o que e futuro da vida", "quem é Gil Giardelli", "quem é Elon Musk", "quem é Steve Jobs", "quem é Bill Gates", "quem é Mark Zuckerberg", 
        "quem é Sundar Pichai", "quem é Satya Nadella", "quem é Tim Cook", "quem é Jeff Bezos", "quem é Larry Page", "quem é Sergey Brin", "quem é Jack Ma", "quem é Ma Huateng", "quem é Zhang Yiming", "quem é Susan Wojcicki", "quem é Sheryl Sandberg", "quem é Marissa Mayer", "quem é Meg Whitman", "quem é Ginni Rometty", "quem é Ursula Burns", "quem é Indra Nooyi",
        "fale sobre Gil Giardelli", "fale sobre Elon Musk", "fale sobre Steve Jobs", "fale sobre Bill Gates", "fale sobre Mark Zuckerberg", "fale sobre Sundar Pichai", "fale sobre Satya Nadella", "fale sobre Tim Cook", "fale sobre Jeff Bezos", "fale sobre Larry Page", "fale sobre Sergey Brin", "fale sobre Jack Ma", "fale sobre Ma Huateng", "fale sobre Zhang Yiming", "fale sobre Susan Wojcicki", "fale sobre Sheryl Sandberg", "fale sobre Marissa Mayer", "fale sobre Meg Whitman", "fale sobre Ginni Rometty", "fale sobre Ursula Burns", "fale sobre Indra Nooyi"
        "fale sobre inteligencia artificial", "fale sobre machine learning", "fale sobre deep learning", "fale sobre redes neurais", "fale sobre processamento de linguagem natural",  "fale sobre visao computacional", "fale sobre robótica", "fale sobre automação", "fale sobre internet das coisas", "fale sobre big data", "fale sobre computação em nuvem", "fale sobre cibersegurança", "fale sobre blockchain", "fale sobre criptomoedas", "fale sobre realidade aumentada", "fale sobre realidade virtual", "fale sobre metaverso", "fale sobre 5g", "fale sobre computação quântica", "fale sobre tecnologia 3d",
        "fale sobre impressao 3d", "fale sobre biotecnologia", "fale sobre nanotecnologia", "fale sobre energia renovavel", "fale sobre sustentabilidade", "fale sobre economia circular", "fale sobre desenvolvimento sustentável", "fale sobre responsabilidade social", "fale sobre ética na tecnologia",
    ],
    "quick_phrases": [],
    "conversation_log": [],
    "available_behaviors": []
}

# Fila de tarefas para evitar conflitos
task_queue = Queue()
# Lock para operações críticas
nao_lock = threading.Lock()

class AIAssistant:
    def __init__(self):
        self.openai_key = config["openai_api_key"]

    def set_openai_key(self, key):
        self.openai_key = key
        config["openai_api_key"] = key

    def perguntar_ia(self, mensagem):
        if not self.openai_key:
            return "OpenAI nao configurado."

        host = "api.openai.com"
        endpoint = "/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.openai_key
        }

        body = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "Voce eh NAO, um robo humanoide. Responda em portugues brasileiro de forma simpatica e sem emoticons somente texto. Maximo 30 palavras."},
                {"role": "user", "content": mensagem}
            ],
            "temperature": 0.7,
            "max_tokens": 60
        }

        try:
            body_json = json.dumps(body)
            conn = httplib.HTTPSConnection(host, timeout=15)
            conn.request("POST", endpoint, body_json, headers)
            response = conn.getresponse()
            
            if response.status != 200:
                conn.close()
                return "Erro na API: {}".format(response.status)
            
            data = response.read()
            conn.close()
            response_json = json.loads(data)
            
            resposta = response_json['choices'][0]['message']['content'].strip()
            
            if isinstance(resposta, unicode):
                resposta = resposta.encode('utf-8', 'ignore')
            
            return resposta

        except Exception as e:
            return "Erro: {}".format(str(e))
        
# Variável global para o módulo de reconhecimento
VoiceRecognizer = None

class VoiceRecognizerModule(ALModule):
    """ Módulo para capturar o evento 'WordRecognized' do NAO de forma reativa. """
    def __init__(self, name):
        ALModule.__init__(self, name)
        self.controller = None
        self.memory = None
        self.is_processing = False
        self.last_recognized = ""
        self.last_time = 0
        self.ignore_until = 0  # Timestamp para ignorar reconhecimentos após fala
        
    def set_controller(self, controller):
        """Define o controlador após a inicialização"""
        self.controller = controller
        try:
            self.memory = ALProxy("ALMemory")
        except Exception as e:
            print("Erro ao conectar ALMemory no módulo: {}".format(e))

    def subscribe(self):
        """ Inscreve-se no evento de reconhecimento de voz. """
        try:
            if not self.memory:
                self.memory = ALProxy("ALMemory")
            self.memory.subscribeToEvent("WordRecognized", self.getName(), "onWordRecognized")
            print("✅ Módulo de voz inscrito no evento 'WordRecognized'.")
            return True
        except Exception as e:
            print("❌ Erro ao se inscrever no evento: {}".format(e))
            return False

    def unsubscribe(self):
        """ Cancela a inscrição do evento. """
        try:
            if self.memory:
                self.memory.unsubscribeFromEvent("WordRecognized", self.getName())
                print("🔇 Módulo de voz cancelou a inscrição do evento.")
        except Exception as e:
            print("⚠️ Erro ao cancelar inscrição: {}".format(e))

    def onWordRecognized(self, key, value, message):
        """ Esta função é chamada AUTOMATICAMENTE pelo NAOqi quando uma palavra é reconhecida. """
        if self.is_processing or not value or not self.controller:
            return

        # Verificar se deve ignorar por estar em período de silêncio pós-fala
        current_time = time.time()
        if current_time < self.ignore_until:
            return

        self.is_processing = True
        try:
            # Extrair palavra reconhecida e confiança
            if len(value) >= 2:
                recognized_text = value[0]
                confidence = value[1]
                
                # Verificações mais rigorosas
                if (recognized_text and 
                    recognized_text != "" and 
                    recognized_text != self.last_recognized and 
                    confidence > config["confidence_threshold"] and
                    (current_time - self.last_time) > 2.0):  # Mínimo 2 segundos entre reconhecimentos
                    
                    # Processar texto de forma segura
                    texto_processado = limpar_texto_para_processamento(recognized_text)
                    
                    print(u"🎤 Reconhecido: '{}' -> '{}' (confiança: {:.2f})".format(
                        safe_str(recognized_text), 
                        safe_str(texto_processado), 
                        confidence
                    ))
                    
                    # Atualizar controles de tempo e repetição
                    self.last_recognized = recognized_text
                    self.last_time = current_time
                    
                    # Definir período de silêncio após reconhecimento (3 segundos)
                    self.ignore_until = current_time + 3.0
                    
                    # Processar comando de forma assíncrona
                    if self.controller:
                        threading.Thread(
                            target=self.controller._process_voice_command, 
                            args=(texto_processado,)
                        ).start()
                
                else:
                    # Log apenas para debugs importantes
                    if confidence > 0 and confidence > config["confidence_threshold"]:
                        if recognized_text == self.last_recognized:
                            print("  - Palavra repetida, ignorando.")
                        elif (current_time - self.last_time) <= 2.0:
                            print("  - Muito rápido após último reconhecimento, ignorando.")
                        else:
                            print("  - Confiança baixa ({:.2f}), ignorando.".format(confidence))
        
        except Exception as e:
            print("❌ Erro no callback onWordRecognized: {}".format(safe_str(str(e))))
        finally:
            # Libera para o próximo reconhecimento
            self.is_processing = False
            # Reset da memória para próxima palavra
            try:
                if self.memory:
                    self.memory.insertData("WordRecognized", ["", 0.0])
            except:
                pass


class NAOController:
    def __init__(self):
        self.nao_ip = config["nao_ip"]
        self.port = config["nao_port"]
        self.connected = False
        self.listening = False
        self.tts = None
        self.asr = None
        self.posture = None
        self.behavior_manager = None
        self.memory = None
        self.ai_assistant = AIAssistant()
        self.broker = None
        self.task_worker_thread = None

    def connect(self, ip=None):
        if ip: self.nao_ip = ip
        if not HAS_NAOQI:
            self.connected = True
            self._load_simulated_behaviors()
            self.start_task_worker()
            return True

        try:
            # Shutdown any existing broker first
            if self.broker:
                try:
                    self.broker.shutdown()
                    time.sleep(0.5)
                except:
                    pass

            print("Iniciando ALBroker...")
            self.broker = ALBroker("NAOqiBroker", "0.0.0.0", 0, self.nao_ip, self.port)
            print("Broker iniciado.")

            print("Conectando proxies ao NAO...")
            self.tts = ALProxy("ALTextToSpeech", self.nao_ip, self.port)
            self.asr = ALProxy("ALSpeechRecognition", self.nao_ip, self.port)
            self.memory = ALProxy("ALMemory", self.nao_ip, self.port)
            self.posture = ALProxy("ALRobotPosture", self.nao_ip, self.port)
            self.behavior_manager = ALProxy("ALBehaviorManager", self.nao_ip, self.port)
            print("Proxies conectados.")

            # Inicializa o nosso módulo de voz customizado
            global VoiceRecognizer
            print("Criando módulo de reconhecimento de voz...")
            VoiceRecognizer = VoiceRecognizerModule("VoiceRecognizer")
            VoiceRecognizer.set_controller(self)
            print("Módulo de voz criado.")

            # Configurações do robô
            self.tts.setLanguage(config["language"])
            self.asr.setLanguage(config["language"])

            self._load_available_behaviors()
            self.add_task('speak', "Sistema conectado e pronto!")
            self.connected = True
            self.start_task_worker()
            return True

        except Exception as e:
            print("❌ Erro detalhado ao conectar: {}".format(e))
            if self.broker:
                try:
                    self.broker.shutdown()
                except:
                    pass
                self.broker = None
            self.connected = False
            return False

    def _load_simulated_behaviors(self):
        storage["available_behaviors"] = [
            {"name": "animations/Stand/Gestures/Hey_1", "category": "Gestos", "description": "Acenar"},
            {"name": "animations/Stand/Gestures/Yes_1", "category": "Gestos", "description": "Sim"},
            {"name": "animations/Stand/Emotions/Positive/Happy_1", "category": "Emocoes", "description": "Feliz"},
            {"name": "animations/Stand/Gestures/Enthusiastic_4", "category": "Gestos", "description": "Danca"}
        ]

    def _load_available_behaviors(self):
        if not self.behavior_manager:
            self._load_simulated_behaviors()
            return
        try:
            behaviors = self.behavior_manager.getInstalledBehaviors()
            storage["available_behaviors"] = []
            for behavior in behaviors:
                category = "Outros"
                if "Gestures" in behavior: category = "Gestos"
                elif "Emotions" in behavior: category = "Emocoes"
                storage["available_behaviors"].append({
                    "name": behavior,
                    "category": category,
                    "description": behavior.split("/")[-1] if "/" in behavior else behavior
                })
        except Exception as e:
            self._load_simulated_behaviors()

    def add_task(self, task_type, data):
        task_queue.put({'type': task_type, 'data': data})

    def start_task_worker(self):
        if self.task_worker_thread and self.task_worker_thread.is_alive():
            return
        self.task_worker_thread = threading.Thread(target=self._task_worker_loop)
        self.task_worker_thread.daemon = True
        self.task_worker_thread.start()
        print("✅ Worker de tarefas iniciado.")

    def _task_worker_loop(self):
        while True:
            try:
                task = task_queue.get(timeout=1)
                task_type = task['type']
                data = task['data']

                if task_type == 'speak': self._execute_speak(data)
                elif task_type == 'behavior': self._execute_behavior(data)
                elif task_type == 'posture': self._execute_posture(data)
                
                task_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                print("❌ Erro no worker de tarefas: {}".format(e))

    def _execute_speak(self, text):
        if not self.connected: return
        self._log_conversation("speak", text, "system")
        if not HAS_NAOQI:
            print("SIMULACAO - NAO: '{}'".format(safe_str(text)))
            return
        try:
            # Pausar reconhecimento enquanto fala
            was_listening = self.listening
            if was_listening and self.asr:
                print("⏸️ Pausando reconhecimento para falar...")
                self.asr.pause(True)
            
            print("🗣️ Falando: '{}'".format(safe_str(text)))
            self.tts.say(safe_str(text))
            print("✅ Fala concluída")
            
            # Aguardar um pouco antes de reativar o reconhecimento
            if was_listening and self.asr:
                time.sleep(1.5)  # Pausa de 1.5 segundos após falar
                print("▶️ Reativando reconhecimento...")
                self.asr.pause(False)
                # Limpar memória para evitar captação de eco
                try:
                    if self.memory:
                        self.memory.insertData("WordRecognized", ["", 0.0])
                        time.sleep(0.2)
                except:
                    pass
                    
        except Exception as e:
            print("❌ Erro no TTS: {}".format(e))
            # Reativar reconhecimento mesmo em caso de erro
            if was_listening and self.asr:
                try:
                    self.asr.pause(False)
                except:
                    pass

    def _execute_posture(self, posture_name):
        if not self.connected or not self.posture: return
        try:
            if HAS_NAOQI:
                self._stop_all_behaviors()
                self.posture.goToPosture(safe_str(posture_name), 0.8)
            self._log_conversation("posture", "Mudando para postura: {}".format(posture_name), "system")
        except Exception as e:
            print("❌ Erro ao mudar de postura: {}".format(e))

    def _stop_all_behaviors(self):
        if not HAS_NAOQI or not self.behavior_manager: return
        try:
            running_behaviors = self.behavior_manager.getRunningBehaviors()
            if running_behaviors:
                print("Parando behaviors em execução: {}".format(running_behaviors))
                for behavior in running_behaviors:
                    self.behavior_manager.stopBehavior(behavior)
                time.sleep(0.5)
        except Exception as e:
            print("⚠️ Aviso ao parar behaviors: {}".format(e))

    def _execute_behavior(self, behavior_name):
        if not self.connected: return
        try:
            behavior_safe = safe_str(behavior_name)
            print("Executando behavior: {}".format(behavior_safe))
            
            if HAS_NAOQI and self.behavior_manager:
                self._stop_all_behaviors()
                if behavior_safe in self.behavior_manager.getInstalledBehaviors():
                    self.behavior_manager.runBehavior(behavior_safe)
                    print("✅ Behavior '{}' iniciado.".format(behavior_safe))
                else:
                    print("❌ Behavior '{}' não encontrado.".format(behavior_safe))
            else:
                print("SIMULACAO - Executando behavior: {}".format(behavior_safe))
            
            self._log_conversation("behavior", "Executando: {}".format(behavior_safe), "system")
        except Exception as e:
            print("❌ ERRO no behavior '{}': {}".format(behavior_name, e))

    def start_voice_recognition(self):
        with nao_lock:
            if self.listening: return True
            if not self.connected or not HAS_NAOQI or not self.asr:
                self.listening = True
                return True
            
            try:
                print("🎤 Iniciando reconhecimento de voz nativo...")
                
                # 1. Cancelar qualquer inscrição anterior primeiro
                try:
                    if VoiceRecognizer:
                        VoiceRecognizer.unsubscribe()
                    time.sleep(0.2)
                except:
                    pass
                
                # 2. Parar completamente o ASR
                try:
                    # Unsubscribe de qualquer coisa que possa estar rodando
                    try:
                        self.asr.unsubscribe("Test_ASR")
                    except:
                        pass
                    
                    # Pausar o ASR
                    self.asr.pause(True)
                    time.sleep(0.5)  # Tempo maior para garantir que pare
                except Exception as e:
                    print("  - Aviso ao parar ASR: {}".format(e))
                
                # 3. Configurar vocabulário agora que está parado
                vocabulary = storage["vocabulary"]
                print("  - Configurando vocabulário com {} palavras".format(len(vocabulary)))
                
                try:
                    self.asr.setVocabulary(vocabulary, False)
                    time.sleep(0.2)
                    print("  - Vocabulário configurado com sucesso")
                except Exception as e:
                    print("❌ Erro ao configurar vocabulário: {}".format(e))
                    return False
                
                # 4. Limpar memória e resetar módulo de voz
                try:
                    self.memory.insertData("WordRecognized", ["", 0.0])
                    if VoiceRecognizer:
                        VoiceRecognizer.last_recognized = ""
                        VoiceRecognizer.last_time = 0
                        VoiceRecognizer.ignore_until = 0
                    time.sleep(0.2)
                except:
                    pass
                
                # 5. Inscrever no evento
                if VoiceRecognizer and VoiceRecognizer.subscribe():
                    print("  - Evento inscrito com sucesso")
                    
                    # 6. Despausar o ASR por último
                    try:
                        self.asr.pause(False)
                        time.sleep(0.3)
                        print("  - ASR ativado")
                        
                        self.listening = True
                        print("✅ Reconhecimento de voz iniciado com sucesso.")
                        print("💡 Dica: Fale claramente e aguarde 2-3 segundos entre comandos")
                        return True
                    except Exception as e:
                        print("❌ Erro ao ativar ASR: {}".format(e))
                        return False
                else:
                    print("❌ Falha ao se inscrever no evento")
                    try: 
                        self.asr.pause(False)
                    except: 
                        pass
                    return False
                
            except Exception as e:
                print("❌ Erro ao iniciar reconhecimento: {}".format(e))
                try: 
                    self.asr.pause(False)
                except: 
                    pass
                self.listening = False
                return False

    def stop_voice_recognition(self):
        with nao_lock:
            if not self.listening: return
            if not HAS_NAOQI or not self.asr:
                self.listening = False
                return

            try:
                print("🔇 Parando reconhecimento de voz...")
                
                # Pausar ASR primeiro
                self.asr.pause(True)
                time.sleep(0.2)
                
                # Cancelar inscrição
                if VoiceRecognizer:
                    VoiceRecognizer.unsubscribe()
                
                # Limpar memória
                try:
                    self.memory.insertData("WordRecognized", ["", 0.0])
                except:
                    pass
                
                self.listening = False
                print("✅ Reconhecimento de voz parado.")
                
            except Exception as e:
                print("⚠️ Erro ao parar reconhecimento: {}".format(e))
            finally:
                # Garantir que o ASR seja despausado para uso futuro
                try: 
                    self.asr.pause(False)
                except: 
                    pass

    def _process_voice_command(self, command):
        """Processa comando de voz de forma thread-safe"""
        try:
            # Log da entrada de voz
            self._log_conversation("voice_input", command, "user")
            found_command = False
            
            # Comandos básicos
            if any(word in command for word in ['ola', 'oi', 'bom dia', 'boa tarde', 'boa noite']):
                self.add_task('speak', 'Olá! Como posso ajudar você hoje?')
                found_command = True
            elif any(word in command for word in ['tchau', 'adeus', 'ate logo']):
                self.add_task('speak', 'Até logo! Foi um prazer conversar com você.')
                found_command = True
            elif any(word in command for word in ['levante', 'em pe', 'levantar']):
                self.add_task('posture', 'Stand')
                self.add_task('speak', 'Estou me levantando agora!')
                found_command = True
            elif any(word in command for word in ['sente', 'sentar', 'senta']):
                self.add_task('posture', 'Sit')
                self.add_task('speak', 'Vou me sentar agora.')
                found_command = True
            elif any(word in command for word in ['dance', 'dancar', 'danca']):
                self.add_task('behavior', 'animations/Stand/Gestures/Enthusiastic_4')
                self.add_task('speak', 'Vamos dançar juntos!')
                found_command = True
            elif any(word in command for word in ['acenar', 'acena']):
                self.add_task('behavior', 'animations/Stand/Gestures/Hey_1')
                self.add_task('speak', 'Olá! Acenar é uma das minhas especialidades.')
                found_command = True
            elif any(word in command for word in ['bateria', 'energia']):
                battery = self.get_battery_level()
                self.add_task('speak', 'Minha bateria está em {} por cento'.format(battery))
                found_command = True
            elif any(word in command for word in ['pare', 'parar', 'para']):
                self.add_task('speak', 'Parando de escutar. Até mais!')
                self.stop_voice_recognition()
                found_command = True
            
            # Se não encontrou comando e tem IA configurada
            if not found_command and config["openai_api_key"]:
                print("💭 Enviando para IA: '{}'".format(command))
                resposta = self.ai_assistant.perguntar_ia(command)
                if resposta and "Erro" not in resposta:
                    self.add_task('speak', resposta)
                    self._log_conversation("ai_response", resposta, "ai")
                else:
                    self.add_task('speak', 'Desculpe, não entendi o comando.')
            elif not found_command:
                self.add_task('speak', 'Desculpe, não entendi o comando.')
                
        except Exception as e:
            print("❌ Erro ao processar comando de voz: {}".format(e))
            self.add_task('speak', 'Desculpe, houve um problema.')

    def get_battery_level(self):
        if not self.connected or not HAS_NAOQI or not self.memory: return 85
        try:
            return int(self.memory.getData("Device/SubDeviceList/Battery/Charge/Sensor/Value") * 100)
        except:
            return 85

    def get_status(self):
        return {
            "connected": self.connected,
            "listening": self.listening,
            "ip": self.nao_ip,
            "battery": int(self.get_battery_level()),
            "simulation": not HAS_NAOQI,
            "vocabulary_size": len(storage["vocabulary"]),
            "ai_configured": bool(config["openai_api_key"])
        }

    def _log_conversation(self, log_type, content, source):
        log_entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": log_type,
            "content": content,
            "source": source
        }
        storage["conversation_log"].append(log_entry)
        if len(storage["conversation_log"]) > 100:
            storage["conversation_log"].pop(0)
            
# Instância global
nao_controller = NAOController()

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NAO Robot Control System</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            min-height: 100vh;
            box-shadow: 0 0 30px rgba(0,0,0,0.2);
        }
        .header {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        .header h1 { font-size: 2em; margin-bottom: 5px; }
        .header p { opacity: 0.9; }
        .nav {
            background: #f8f9fa;
            padding: 0;
            border-bottom: 1px solid #dee2e6;
            overflow-x: auto;
        }
        .nav-tabs {
            display: flex;
            min-width: 600px;
        }
        .nav-tab {
            flex: 1;
            padding: 15px 20px;
            background: #f8f9fa;
            border: none;
            cursor: pointer;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
            font-weight: 500;
        }
        .nav-tab:hover { background: #e9ecef; }
        .nav-tab.active {
            background: white;
            border-bottom-color: #667eea;
            color: #667eea;
        }
        .content {
            padding: 20px;
            min-height: 400px;
        }
        .page {
            display: none;
            animation: fadeIn 0.3s ease-in;
        }
        .page.active { display: block; }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 3px 15px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        .card h3 { color: #333; margin-bottom: 15px; font-size: 1.2em; }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .status-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .status-item strong { display: block; color: #667eea; margin-bottom: 5px; }
        .status.success { background: #d4edda; color: #155724; padding: 10px; border-radius: 5px; }
        .status.error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 5px; }
        .status.info { background: #d1ecf1; color: #0c5460; padding: 10px; border-radius: 5px; }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s;
            margin: 5px;
            display: inline-block;
        }
        .btn-primary {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
        }
        .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4); }
        .btn:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        .btn-success { background: #28a745; color: white; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-secondary { background: #6c757d; color: white; }
        .form-control {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            margin: 5px 0;
        }
        .log-container {
            background: #1e1e1e;
            color: #fff;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            max-height: 400px;
            overflow-y: auto;
            margin: 10px 0;
        }
        .log-entry {
            padding: 5px 0;
            border-bottom: 1px solid #333;
        }
        .log-time { color: #888; }
        .log-user { color: #4CAF50; }
        .log-ai { color: #2196F3; }
        .log-system { color: #FF9800; }
        .table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .table th, .table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }
        .table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }
        .table tbody tr:hover { background: #f8f9fa; }
        @media (max-width: 768px) {
            .container { margin: 0; }
            .header { padding: 15px; }
            .header h1 { font-size: 1.5em; }
            .content { padding: 15px; }
            .status-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 5º ERA - NAO Control System</h1>
            <p>Sistema de Controle com IA Integrada</p>
        </div>

        <div class="nav">
            <div class="nav-tabs">
                <button class="nav-tab active" onclick="showPage('home')">🏠 Home</button>
                <button class="nav-tab" onclick="showPage('quick')">⚡ Comandos</button>
                <button class="nav-tab" onclick="showPage('movements')">🤸 Movimentos</button>
                <button class="nav-tab" onclick="showPage('speech')">🗣️ Fala</button>
                <button class="nav-tab" onclick="showPage('config')">⚙️ Configuração</button>
            </div>
        </div>

        <div class="content">
            <!-- HOME PAGE -->
            <div id="home" class="page active">
                <div class="card">
                    <h3>📊 Status do Sistema</h3>
                    <div id="mainStatus" class="status info">🔄 Carregando...</div>
                    
                    <div class="status-grid">
                        <div class="status-item">
                            <strong>Conexão NAO</strong>
                            <span id="connectionStatus">Verificando...</span>
                        </div>
                        <div class="status-item">
                            <strong>Escuta Ativa</strong>
                            <span id="listeningStatus">Inativa</span>
                        </div>
                        <div class="status-item">
                            <strong>IA Configurada</strong>
                            <span id="aiStatus">Verificando...</span>
                        </div>
                        <div class="status-item">
                            <strong>Bateria</strong>
                            <span id="batteryStatus">--</span>
                        </div>
                    </div>

                    <div style="text-align: center; margin: 20px 0;">
                        <button id="connectBtn" class="btn btn-primary" onclick="connectNAO()">🔌 Conectar NAO</button>
                        <button id="startBtn" class="btn btn-success" onclick="startListening()" disabled>🎤 Iniciar Escuta NAO</button>
                        <button id="stopBtn" class="btn btn-danger" onclick="stopListening()" disabled>🛑 Parar Escuta</button>
                        <br><br>
                        <button class="btn btn-secondary" onclick="testSpeech()">🗣️ Teste de Fala</button>
                    </div>
                </div>

                <div class="card">
                    <h3>💬 Log de Conversação</h3>
                    <div class="log-container" id="conversationLog">
                        <div class="log-entry">
                            <span class="log-time">[Sistema]</span> 
                            <span class="log-system">Aguardando conexão...</span>
                        </div>
                    </div>
                    <button class="btn btn-secondary" onclick="clearLog()">🗑️ Limpar Log</button>
                </div>

                <div class="card">
                    <h3>🌐 Informações de Rede</h3>
                    <p><strong>IP Principal:</strong> <span id="mainIP">Detectando...</span></p>
                    <p><strong>Modo:</strong> <span id="modeInfo">Verificando...</span></p>
                </div>
            </div>

            <!-- CONFIG PAGE -->
            <div id="config" class="page">
                <div class="card">
                    <h3>🤖 Configuração OpenAI</h3>
                    <input type="password" id="openaiKey" class="form-control" placeholder="Chave da API OpenAI">
                    <button class="btn btn-primary" onclick="saveAIConfig()">💾 Salvar</button>
                    <button class="btn btn-success" onclick="testAI()">🧪 Testar</button>
                </div>

                <div class="card">
                    <h3>📚 Vocabulário</h3>
                    <p>Total de palavras: <span id="vocabCount">0</span></p>
                    <input type="text" id="newVocabWord" class="form-control" placeholder="Nova palavra...">
                    <button class="btn btn-primary" onclick="addVocabWord()">➕ Adicionar</button>
                </div>
            </div>

            <!-- QUICK COMMANDS PAGE -->
            <div id="quick" class="page">
                <div class="card">
                    <h3>⚡ Comandos Rápidos</h3>
                    <div class="status-grid">
                         <button class="btn btn-primary" onclick="quickCommand('behavior', 'falardevoce')">👋 Falar de você</button>
                        <button class="btn btn-primary" onclick="quickCommand('posture', 'Stand')">🧍 Em Pé</button>
                        <button class="btn btn-primary" onclick="quickCommand('posture', 'Sit')">🪑 Sentar</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'animations/Stand/Gestures/Hey_1')">👋 Acenar</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'triller')">Dança - triller</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'caravan-palace')">Dança - caravan-palace</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'taichi-dance')">Dança - taichi-dance</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'gangnam-style')">Dança - gangnam-style</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'little-apple-ca0896')">Dança - little-apple</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'harder-better-faster-stronger-9d8299')">Dança - harder-better-faster</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'heyo/behavior_1')">Dança - heya</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'madonna-nicki-minaj/behavior_1')">Dança - madonna-nicki-minaj</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'vangelis/vangelis')">Dança - vangelis</button>
                        <button class="btn btn-primary" onclick="quickCommand('behavior', 'sleep-reactions/TouchHand')">Dança - TouchHand</button>



                        <button class="btn btn-primary" onclick="quickCommand('speak', 'Minha bateria está OK')">🔋 Status</button>
                    </div>
                </div>

                <div class="card">
                    <h3>🎮 Controle Manual</h3>
                    <input type="text" id="customSpeakText" class="form-control" placeholder="Digite o que o NAO deve falar...">
                    <button class="btn btn-success" onclick="customSpeak()">🗣️ Falar</button>
                </div>
            </div>

            <!-- MOVEMENTS PAGE -->
            <div id="movements" class="page">
                <div class="card">
                    <h3>🤸 Movimentos Disponíveis</h3>
                    <div id="loadingMovements" class="status info">🔄 Carregando movimentos...</div>
                    <table class="table" id="movementsTable" style="display: none;">
                        <thead>
                            <tr>
                                <th>Categoria</th>
                                <th>Nome</th>
                                <th>Ação</th>
                            </tr>
                        </thead>
                        <tbody id="movementsBody"></tbody>
                    </table>
                </div>
            </div>

            <!-- SPEECH PAGE -->
            <div id="speech" class="page">
                <div class="card">
                    <h3>🗣️ Controle de Fala</h3>
                    <textarea id="speechText" class="form-control" placeholder="Digite o que o NAO deve falar..." rows="4"></textarea>
                    <button class="btn btn-primary" onclick="speakText()">🎵 Falar</button>
                </div>

                <div class="card">
                    <h3>💾 Frases Salvas</h3>
                    <input type="text" id="newPhraseTitle" class="form-control" placeholder="Título da frase...">
                    <input type="text" id="newPhraseText" class="form-control" placeholder="Texto da frase...">
                    <button class="btn btn-success" onclick="saveQuickPhrase()">💾 Salvar</button>
                    
                    <table class="table" id="phrasesTable">
                        <thead>
                            <tr>
                                <th>Título</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="phrasesBody"></tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>

    <script>
        var systemStatus = {};
        var currentPage = 'home';
        var logPollingInterval = null;

        function showPage(pageId) {
            var pages = document.querySelectorAll('.page');
            for (var i = 0; i < pages.length; i++) {
                pages[i].classList.remove('active');
            }
            
            var targetPage = document.getElementById(pageId);
            if (targetPage) {
                targetPage.classList.add('active');
            }
            
            var tabs = document.querySelectorAll('.nav-tab');
            for (var i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            
            var pageNames = ['home', 'config', 'quick', 'movements', 'speech'];
            var pageIndex = pageNames.indexOf(pageId);
            if (pageIndex >= 0 && tabs[pageIndex]) {
                tabs[pageIndex].classList.add('active');
            }
            
            currentPage = pageId;
            
            if (pageId === 'movements') {
                loadMovements();
            } else if (pageId === 'speech') {
                loadQuickPhrases();
            }
        }

        function connectNAO() {
            updateMainStatus('Conectando ao NAO...', 'info');
            
            fetch('/connect_nao', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({})
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    updateMainStatus('NAO conectado com sucesso!', 'success');
                    addLogEntry('Sistema', 'NAO conectado com sucesso', 'system');
                } else {
                    updateMainStatus('Erro ao conectar: ' + (data.error || 'Erro desconhecido'), 'error');
                }
                updateSystemInfo();
            })
            .catch(function(error) {
                updateMainStatus('Erro de conexão: ' + error.message, 'error');
            });
        }

        function startListening() {
            updateMainStatus('Iniciando escuta...', 'info');
            
            fetch('/start_listening', {method: 'POST'})
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    systemStatus.listening = true;
                    updateMainStatus('NAO escutando - use comandos de voz', 'success');
                    addLogEntry('Sistema', 'Reconhecimento de voz ativo', 'system');
                    startLogPolling();
                } else {
                    updateMainStatus('Erro ao iniciar escuta: ' + (data.error || 'desconhecido'), 'error');
                }
                updateSystemInfo();
            })
            .catch(function(error) {
                updateMainStatus('Erro: ' + error.message, 'error');
            });
        }

        function stopListening() {
            fetch('/stop_listening', {method: 'POST'})
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    systemStatus.listening = false;
                    updateMainStatus('Escuta parada', 'info');
                    addLogEntry('Sistema', 'Reconhecimento de voz parado', 'system');
                    stopLogPolling();
                } else {
                    updateMainStatus('Erro ao parar escuta', 'error');
                }
                updateSystemInfo();
            });
        }

        function updateSystemInfo() {
            fetch('/nao/status')
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                systemStatus = data;
                
                safeUpdateElement('connectionStatus', data.connected ? 'Conectado' : 'Desconectado');
                safeUpdateElement('listeningStatus', data.listening ? 'Ativa (NAO)' : 'Inativa');
                safeUpdateElement('aiStatus', data.ai_configured ? 'Configurada' : 'Não');
                safeUpdateElement('batteryStatus', data.battery + '%');
                safeUpdateElement('mainIP', data.ip);
                safeUpdateElement('modeInfo', data.simulation ? 'Simulação' : 'Real');
                safeUpdateElement('vocabCount', data.vocabulary_size);
                
                updateControls();
                
                if (data.connected && data.listening) {
                    updateMainStatus('NAO ouvindo - fale comandos', 'success');
                } else if (data.connected) {
                    updateMainStatus('NAO conectado - pronto', 'success');
                } else {
                    updateMainStatus('NAO desconectado', 'info');
                }
            })
            .catch(function(error) {
                updateMainStatus('Erro de comunicação', 'error');
            });
        }

        function safeUpdateElement(id, value) {
            var element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        }

        function updateControls() {
            var connected = systemStatus.connected || false;
            var listening = systemStatus.listening || false;
            
            var connectBtn = document.getElementById('connectBtn');
            var startBtn = document.getElementById('startBtn');
            var stopBtn = document.getElementById('stopBtn');
            
            if (connectBtn) connectBtn.disabled = connected;
            if (startBtn) startBtn.disabled = !connected || listening;
            if (stopBtn) stopBtn.disabled = !listening;
        }

        function updateMainStatus(message, type) {
            var statusEl = document.getElementById('mainStatus');
            if (statusEl) {
                statusEl.textContent = message;
                statusEl.className = 'status ' + type;
            }
        }

        function startLogPolling() {
            if (logPollingInterval) clearInterval(logPollingInterval);
            logPollingInterval = setInterval(updateConversationLog, 2000);
        }

        function stopLogPolling() {
            if (logPollingInterval) {
                clearInterval(logPollingInterval);
                logPollingInterval = null;
            }
        }

        function updateConversationLog() {
            fetch('/get_conversation_log')
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                var logContainer = document.getElementById('conversationLog');
                if (!logContainer || !data.log) return;
                
                logContainer.innerHTML = '';
                
                if (data.log.length > 0) {
                    var logsToShow = data.log.slice(-20);
                    for (var i = 0; i < logsToShow.length; i++) {
                        var entry = logsToShow[i];
                        var logDiv = document.createElement('div');
                        logDiv.className = 'log-entry';
                        
                        var timeSpan = document.createElement('span');
                        timeSpan.className = 'log-time';
                        timeSpan.textContent = '[' + entry.timestamp + '] ';
                        
                        var contentSpan = document.createElement('span');
                        contentSpan.className = 'log-' + entry.source;
                        
                        var prefix = '';
                        if (entry.source === 'user') prefix = 'Usuário: ';
                        else if (entry.source === 'ai') prefix = 'IA: ';
                        else prefix = 'Sistema: ';
                        
                        contentSpan.textContent = prefix + entry.content;
                        
                        logDiv.appendChild(timeSpan);
                        logDiv.appendChild(contentSpan);
                        logContainer.appendChild(logDiv);
                    }
                    
                    logContainer.scrollTop = logContainer.scrollHeight;
                } else {
                    logContainer.innerHTML = '<div class="log-entry"><span class="log-time">[Sistema]</span> <span class="log-system">Aguardando atividades...</span></div>';
                }
            });
        }

        function addLogEntry(source, content, type) {
            var logContainer = document.getElementById('conversationLog');
            if (!logContainer) return;
            
            var logDiv = document.createElement('div');
            logDiv.className = 'log-entry';
            
            var now = new Date();
            var timeStr = now.toLocaleTimeString();
            
            logDiv.innerHTML = '<span class="log-time">[' + timeStr + ']</span> <span class="log-' + type + '">' + source + ': ' + content + '</span>';
            
            logContainer.appendChild(logDiv);
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        function clearLog() {
            fetch('/clear_conversation_log', {method: 'POST'})
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    var logContainer = document.getElementById('conversationLog');
                    if (logContainer) {
                        logContainer.innerHTML = '<div class="log-entry"><span class="log-time">[Sistema]</span> <span class="log-system">Log limpo</span></div>';
                    }
                }
            });
        }

        function quickCommand(type, command) {
            var endpoint = '';
            var body = {};
            
            if (type === 'speak') {
                endpoint = '/nao/speak';
                body = {text: command};
            } else if (type === 'posture') {
                endpoint = '/nao/posture';
                body = {posture: command};
            } else if (type === 'behavior') {
                endpoint = '/nao/behavior';
                body = {behavior: command};
            }
            
            fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body)
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    addLogEntry('Sistema', 'Comando executado: ' + type + ' - ' + command, 'system');
                } else {
                    addLogEntry('Sistema', 'Erro no comando: ' + (data.error || 'desconhecido'), 'system');
                }
            });
        }

        function customSpeak() {
            var text = document.getElementById('customSpeakText');
            if (!text || !text.value.trim()) {
                alert('Digite um texto!');
                return;
            }
            
            quickCommand('speak', text.value.trim());
            text.value = '';
        }

        function saveAIConfig() {
            var key = document.getElementById('openaiKey');
            if (!key || !key.value.trim()) {
                alert('Digite a chave da API!');
                return;
            }
            
            fetch('/save_ai_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    provider: 'openai',
                    openai_key: key.value.trim()
                })
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    alert('Configuração salva!');
                    updateSystemInfo();
                } else {
                    alert('Erro: ' + data.error);
                }
            });
        }

        function testAI() {
            fetch('/test_ai', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({pergunta: 'Olá, como você está?'})
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    alert('IA funcionando!\\n\\nResposta: ' + data.resposta);
                } else {
                    alert('Erro: ' + data.error);
                }
            });
        }

        function addVocabWord() {
            var wordInput = document.getElementById('newVocabWord');
            if (!wordInput || !wordInput.value.trim()) return;
            
            fetch('/add_vocab_word', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({word: wordInput.value.trim()})
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    wordInput.value = '';
                    updateSystemInfo();
                    addLogEntry('Sistema', 'Palavra adicionada ao vocabulário', 'system');
                } else {
                    alert('Erro: ' + data.error);
                }
            });
        }

        function loadMovements() {
            var loading = document.getElementById('loadingMovements');
            var table = document.getElementById('movementsTable');
            
            if (loading) loading.style.display = 'block';
            if (table) table.style.display = 'none';
            
            fetch('/get_movements')
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (loading) loading.style.display = 'none';
                if (table) table.style.display = 'table';
                
                var tbody = document.getElementById('movementsBody');
                if (tbody && data.movements) {
                    tbody.innerHTML = '';
                    for (var i = 0; i < data.movements.length; i++) {
                        var movement = data.movements[i];
                        var row = document.createElement('tr');
                        
                        var categoryCell = document.createElement('td');
                        categoryCell.textContent = movement.category;
                        
                        var nameCell = document.createElement('td');
                        nameCell.textContent = movement.description;
                        
                        var actionCell = document.createElement('td');
                        
                        var playBtn = document.createElement('button');
                        playBtn.className = 'btn btn-success';
                        playBtn.textContent = 'Play';
                        playBtn.onclick = function(behaviorName) {
                            return function() {
                                executeMovement(behaviorName);
                            };
                        }(movement.name);
                        
                        actionCell.appendChild(playBtn);
                        
                        row.appendChild(categoryCell);
                        row.appendChild(nameCell);
                        row.appendChild(actionCell);
                        tbody.appendChild(row);
                    }
                }
            });
        }

        function executeMovement(name) {
            addLogEntry('Sistema', 'Iniciando movimento: ' + name, 'system');
            quickCommand('behavior', name);
        }

        function speakText() {
            var text = document.getElementById('speechText');
            if (!text || !text.value.trim()) {
                alert('Digite um texto!');
                return;
            }
            
            quickCommand('speak', text.value.trim());
        }

        function saveQuickPhrase() {
            var title = document.getElementById('newPhraseTitle');
            var text = document.getElementById('newPhraseText');
            
            if (!title || !text || !title.value.trim() || !text.value.trim()) {
                alert('Preencha título e texto!');
                return;
            }
            
            fetch('/save_quick_phrase', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    title: title.value.trim(),
                    text: text.value.trim()
                })
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                if (data.success) {
                    title.value = '';
                    text.value = '';
                    loadQuickPhrases();
                } else {
                    alert('Erro: ' + data.error);
                }
            });
        }

        function loadQuickPhrases() {
            fetch('/get_quick_phrases')
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                var tbody = document.getElementById('phrasesBody');
                if (tbody && data.phrases) {
                    tbody.innerHTML = '';
                    for (var i = 0; i < data.phrases.length; i++) {
                        var phrase = data.phrases[i];
                        var row = document.createElement('tr');
                        
                        var titleCell = document.createElement('td');
                        titleCell.textContent = phrase.title;
                        
                        var actionsCell = document.createElement('td');
                        
                        var playBtn = document.createElement('button');
                        playBtn.className = 'btn btn-success';
                        playBtn.textContent = 'Play';
                        playBtn.onclick = function(text) {
                            return function() {
                                quickCommand('speak', text);
                            };
                        }(phrase.text);
                        
                        var deleteBtn = document.createElement('button');
                        deleteBtn.className = 'btn btn-danger';
                        deleteBtn.textContent = 'Delete';
                        deleteBtn.onclick = function(index) {
                            return function() {
                                deletePhrase(index);
                            };
                        }(i);
                        
                        actionsCell.appendChild(playBtn);
                        actionsCell.appendChild(deleteBtn);
                        
                        row.appendChild(titleCell);
                        row.appendChild(actionsCell);
                        tbody.appendChild(row);
                    }
                }
            });
        }

        function deletePhrase(index) {
            if (confirm('Excluir esta frase?')) {
                fetch('/delete_quick_phrase', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({index: index})
                })
                .then(function(response) {
                    return response.json();
                })
                .then(function(data) {
                    if (data.success) {
                        loadQuickPhrases();
                    }
                });
            }
        }

        function testSpeech() {
            addLogEntry('Sistema', 'Testando sistema de fala...', 'system');
            quickCommand('speak', 'Teste de fala funcionando perfeitamente! Sistema NAO operacional.');
        }

        window.onload = function() {
            try {
                updateMainStatus('Sistema carregado - verificando status...', 'info');
                addLogEntry('Sistema', 'Sistema iniciado - usando reconhecimento NAO nativo', 'system');
                
                setTimeout(function() {
                    updateSystemInfo();
                }, 1000);
                
                setInterval(updateSystemInfo, 10000);
                
                setTimeout(function() {
                    updateConversationLog();
                }, 2000);
                
            } catch(error) {
                updateMainStatus('Erro na inicialização: ' + error.message, 'error');
            }
        };
    </script>
</body>
</html>'''

# === ROTAS DA API ===
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/connect_nao', methods=['POST'])
def connect_nao():
    try:
        success = nao_controller.connect()
        return jsonify({"success": success, "ip": nao_controller.nao_ip})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/nao/status', methods=['GET'])
def nao_status():
    try:
        status = nao_controller.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"connected": False, "error": str(e)}), 500

@app.route('/nao/speak', methods=['POST'])
def nao_speak():
    data = request.get_json()
    text = data.get('text')
    if not text: return jsonify({"success": False, "error": "Texto vazio"}), 400
    nao_controller.add_task('speak', text)
    return jsonify({"success": True, "message": "Comando de fala enfileirado."})

@app.route('/nao/posture', methods=['POST'])
def nao_posture():
    data = request.get_json()
    posture = data.get('posture')
    if not posture: return jsonify({"success": False, "error": "Postura vazia"}), 400
    nao_controller.add_task('posture', posture)
    return jsonify({"success": True, "message": "Comando de postura enfileirado."})

@app.route('/nao/behavior', methods=['POST'])
def nao_behavior():
    data = request.get_json()
    behavior = data.get('behavior')
    if not behavior: return jsonify({"success": False, "error": "Behavior vazio"}), 400
    nao_controller.add_task('behavior', behavior)
    return jsonify({"success": True, "message": "Comando de behavior enfileirado."})

@app.route('/start_listening', methods=['POST'])
def start_listening():
    success = nao_controller.start_voice_recognition()
    if success:
        nao_controller.add_task('speak', "Estou escutando. Pode falar comigo!")
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Falha ao iniciar escuta."})

@app.route('/stop_listening', methods=['POST'])
def stop_listening():
    nao_controller.stop_voice_recognition()
    nao_controller.add_task('speak', "Parando de escutar. Até logo!")
    return jsonify({"success": True})

@app.route('/save_ai_config', methods=['POST'])
def save_ai_config():
    try:
        data = request.get_json()
        config["openai_api_key"] = data.get("openai_key", "")
        nao_controller.ai_assistant.set_openai_key(config["openai_api_key"])
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/test_ai', methods=['POST'])
def test_ai():
    try:
        data = request.get_json()
        pergunta = data.get('pergunta', 'Teste')
        resposta = nao_controller.ai_assistant.perguntar_ia(pergunta)
        return jsonify({"success": True, "pergunta": pergunta, "resposta": resposta})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/get_conversation_log', methods=['GET'])
def get_conversation_log():
    return jsonify({"log": storage["conversation_log"]})

@app.route('/clear_conversation_log', methods=['POST'])
def clear_conversation_log():
    storage["conversation_log"] = []
    return jsonify({"success": True})

@app.route('/add_vocab_word', methods=['POST'])
def add_vocab_word():
    try:
        data = request.get_json()
        word = data.get('word', '').strip().lower()
        if word and word not in storage["vocabulary"]:
            storage["vocabulary"].append(word)
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Palavra inválida"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/get_movements', methods=['GET'])
def get_movements():
    return jsonify({"movements": storage["available_behaviors"]})

@app.route('/save_quick_phrase', methods=['POST'])
def save_quick_phrase():
    try:
        data = request.get_json()
        title = data.get('title', '').strip()
        text = data.get('text', '').strip()
        if title and text:
            storage["quick_phrases"].append({"title": title, "text": text})
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Título e texto obrigatórios"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/get_quick_phrases', methods=['GET'])
def get_quick_phrases():
    return jsonify({"phrases": storage["quick_phrases"]})

@app.route('/delete_quick_phrase', methods=['POST'])
def delete_quick_phrase():
    try:
        data = request.get_json()
        index = data.get('index', -1)
        if 0 <= index < len(storage["quick_phrases"]):
            storage["quick_phrases"].pop(index)
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Índice inválido"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def auto_start_system():
    print("=" * 60)
    print("  NAO ROBOT CONTROL SYSTEM - RECONHECIMENTO NATIVO")
    print("=" * 60)
    print("  IP detectado: {}".format(NAO_IP))
    print("  IA configurada: {}".format(bool(config["openai_api_key"])))
    print("=" * 60)

    if config["auto_connect_ai"]:
        print("Conectando automaticamente ao NAO...")
        if nao_controller.connect():
            print("NAO conectado automaticamente!")
        else:
            print("Erro na conexão automática")

    print("\nInterface web disponível em:")
    print("  http://{}:{}".format(config["flask_host"], config["flask_port"]))
    print("")

if __name__ == '__main__':
    try:
        auto_start_system()
        
        print("Iniciando servidor Flask...")
        app.run(
            host=config["flask_host"],
            port=config["flask_port"],
            debug=False,
            use_reloader=False,
            threaded=True
        )

    except KeyboardInterrupt:
        print("\nSistema finalizado pelo usuário.")
        if nao_controller.broker:
            try:
                nao_controller.broker.shutdown()
            except:
                pass
    except Exception as e:
        print("\nErro fatal ao iniciar: {}".format(e))
        if nao_controller.broker:
            try:
                nao_controller.broker.shutdown()
            except:
                pass
