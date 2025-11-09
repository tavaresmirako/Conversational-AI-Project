import os
import time
import speech_recognition as sr
from dotenv import load_dotenv
import boto3
import requests
from googletrans import Translator
import pygame  # Importa a biblioteca pygame

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Função para capturar áudio do microfone
def capture_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Aguardando sua pergunta... Você tem até 20 segundos para falar!")
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=20)
        except sr.WaitTimeoutError:
            print("Tempo limite excedido. Nenhuma pergunta foi detectada.")
            return None

    try:
        text = recognizer.recognize_google(audio, language="pt-BR")
        print(f"Texto transcrito: {text}")
        return text
    except Exception as e:
        print(f"Erro ao transcrever o áudio: {e}")
        return None

# Função para gerar resposta via LM Studio
def generate_response(prompt):
    print(f"Gerando resposta para: '{prompt}'")
    try:
        url = "http://localhost:1234/v1/chat/completions"
        payload = {
            "model": "deepseek-r1-distill-qwen-1.5b",  # Nome exato do modelo no LM Studio
            "messages": [
                {"role": "system", "content": "Você é um assistente que responde apenas em português."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 50
        }
        response = requests.post(url, json=payload, timeout=10)  # Timeout de 10 segundos
        if response.status_code == 200:
            result = response.json()
            generated_text = result["choices"][0]["message"]["content"]
            print(f"Resposta gerada: '{generated_text}'")
            return clean_response(generated_text)  # Limpa a resposta antes de retornar
        else:
            print(f"Erro ao gerar resposta: {response.status_code} - {response.text}")
            return "Desculpe, não consegui processar sua pergunta."
    except requests.exceptions.ConnectionError as e:
        print(f"Erro de conexão com o servidor: {e}")
        return "Desculpe, ocorreu um erro ao conectar ao servidor."
    except Exception as e:
        print(f"Erro ao gerar resposta com a IA: {e}")
        return "Desculpe, ocorreu um erro ao processar sua pergunta."

# Função para limpar a resposta
def clean_response(text):
    """
    Remove tags indesejadas como <think> e outras marcações do texto gerado.
    """
    import re
    cleaned_text = re.sub(r'<[^>]+>', '', text).strip()
    return cleaned_text

# Função para traduzir automaticamente para português
def translate_to_portuguese(text):
    """
    Traduz o texto para português usando a biblioteca googletrans.
    """
    translator = Translator()
    try:
        # Corrigido: 'dsest' para 'dest'
        translated = translator.translate(text, src='auto', dest='pt')
        return translated.text
    except Exception as e:
        print(f"Erro ao traduzir texto: {e}")
        return text  # Retorna o texto original em caso de erro

# Função para converter texto em fala usando Amazon Polly
def text_to_speech_polly(text, output_audio_path="response.mp3"):
    """
    Converte texto em fala usando o Amazon Polly.
    As credenciais são carregadas do arquivo .env.
    """
    polly_client = boto3.client(
        "polly",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),  # Usa variável de ambiente
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),  # Usa variável de ambiente
        region_name=os.getenv("AWS_REGION", "us-east-1")  # Usa variável de ambiente
    )

    try:
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",  # Formato do arquivo de saída
            VoiceId="Camila"    # Voz em português do Brasil
        )

        with open(output_audio_path, "wb") as audio_file:
            audio_file.write(response["AudioStream"].read())
        print(f"Áudio salvo em: {output_audio_path}")
        return output_audio_path

    except Exception as e:
        print(f"Erro ao converter texto em fala com Amazon Polly: {e}")
        return None

# Função para reproduzir áudio usando pygame
def play_audio(audio_path):
    print(f"Reproduzindo áudio: {audio_path}")
    if not os.path.exists(audio_path):
        print(f"Erro: O arquivo de áudio '{audio_path}' não foi encontrado.")
        return

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(audio_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():  # Espera a reprodução terminar
            pygame.time.Clock().tick(10)
        pygame.mixer.quit()
    except pygame.error as e:
        print(f"Erro ao reproduzir o áudio com pygame: {e}")

# Função para fornecer feedback visual/auditivo
def provide_feedback():
    print("Processando...")
    for _ in range(3):
        print(".", end="", flush=True)
        time.sleep(0.5)
    print("\n")

# Fluxo principal
if __name__ == "__main__":
    # Inicializa o mixer do pygame antes do loop principal
    try:
        pygame.mixer.init()
    except pygame.error as e:
        print(f"Aviso: Não foi possível inicializar o mixer do pygame: {e}. A reprodução de áudio pode não funcionar.")

    while True:
        question = capture_audio()

        if not question:
            print("Nenhuma pergunta foi detectada. Tente novamente.")
            continue

        # Feedback visual/auditivo
        provide_feedback()

        response = generate_response(question)

        # Traduz a resposta para português, se necessário
        response = translate_to_portuguese(response)

        output_audio_file = "response.mp3"
        audio_path = text_to_speech_polly(response, output_audio_file)

        if audio_path:
            play_audio(audio_path)
        else:
            print("Falha ao gerar ou reproduzir a resposta.")

        continue_chat = input("Deseja fazer outra pergunta? (s/n): ").strip().lower()
        if continue_chat != 's':
            print("Encerrando o sistema. Até logo!")
            break
