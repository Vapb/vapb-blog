---
title: Configurando um Webhook no Microsoft Teams
author: "vapb"
description: Um breve tutorial com exemplo prático para configurar e testar um webhook no Microsoft Teams.
date: 2025-01-17
tags: ["microsoft-teams", "python"]
toc: true
---

## Introdução

Imagine que seu sistema está funcionando normalmente, quando de repente ocorre um evento crítico. Nesse momento, é essencial notificar imediatamente sua equipe e as partes envolvidas. Em vez de depender de e-mails ou atualizações manuais, você pode automatizar o envio de alertas em tempo real diretamente para um canal do Microsoft Teams. Essa abordagem garante que sua equipe receba informações rápidas e possa agir imediatamente, minimizando o impacto do incidente.

Em sistemas dinâmicos, a comunicação eficiente é vital para a operação. Enviar notificações diretamente para os stakeholders e a equipe é uma maneira prática de manter todos informados. Neste post, vamos mostrar como configurar um webhook no Microsoft Teams para tornar esse processo ainda mais ágil.


## O Que São Webhooks?

Um webhook, por definição, é uma comunicação leve e orientada a eventos, que envia dados automaticamente entre aplicações via HTTP, sem a necessidade de consultas contínuas (polling). Em outras palavras, é uma forma de fazer um sistema fornecer informações em tempo real para outros sistemas, permitindo que um aplicativo envie uma notificação para outro quando um determinado evento ocorre.

Sem me aprofundar muito no conceito de webhook e seus detalhes, resumidamente temos dois sistemas: o **Sender** (Aplicação de Origem), que envia a notificação quando um evento ocorre, e o **Receiver** (Aplicação de Destino), que é o sistema que recebe os dados enviados pelo webhook.

O fluxo do webhook geralmente ocorre da seguinte maneira:
* O **Receiver** registra uma URL pública para onde quer receber os dados, essencialmente um endpoint.
* O **Sender** é configurado para enviar uma mensagem HTTP (geralmente um POST) para essa URL sempre que um evento específico ocorre.
* O **Receiver** processa os dados e executa as ações necessárias.


## Webhooks no Microsoft Teams

Um webhook no Microsoft Teams é um mecanismo que permite a integração de sistemas externos com canais do Teams. Ele funciona como um ponto de entrada que recebe mensagens de outros serviços ou aplicativos e as exibe diretamente em um canal do Teams nos permitindo atualizações em tempo real.

Existem dois tipos de weebhooks Microsoft Teams: 
* **Inbound Webhooks (Webhooks de Entrada)**: São usados para receber mensagens de sistemas externos. Ou seja, um serviço envia uma requisição HTTP POST para a URL do webhook do Teams, e a mensagem é processada e exibida no canal.
* **Outgoing Webhooks (Webhooks de Saída)**: São usados para enviar mensagens do Teams para um serviço externo. 

Nesse tutorial iremos focar nos **Inbound Webhooks (Webhooks de Entrada)**, já que no nosso scenario queremos um sistema que envie mensagens para um chat/canal do teams alertando as partente interradas dos eventos criticos que estão ocorrendo no nosso sistema.

**TeamsIncomingWebhookTrigger** Este trigger permite iniciar um fluxo fazendo uma requisição POST para o endpoint exposto pelo trigger. Você pode enviar um array de adaptive cards no corpo da requisição para o trigger, que serão usados em ações posteriores do fluxo. Este trigger suporta apenas requisições POST e não suporta requisições GET.

Abaixo podemos observar o Request Body Schema.

**Request Body**
| Name        | Key         | Required | Type            | Description                                                                              |
|:-----------:|:-----------:|:--------:|:---------------:|:----------------------------------------------------------------------------------------:|
| type        | type        | yes      | string          | Value should always be `"message"`.                                                      |
| attachments | attachments | yes      | array of object | Array of adaptive card item objects. See AdaptiveCardItemSchema below for object schema. |

**AdaptiveCardItemSchema**
|Name        | Key         | Required | Type   | Description                                                                                              |
|:----------:|:-----------:|:--------:|:------:|:--------------------------------------------------------------------------------------------------------:|
|contentType | contentType | yes      | string | Value should always be `"application/vnd.microsoft.card.adaptive"`.                                      |
|contentUrl  | contentUrl  | yes      | string | Value should always be `null`.                                                                           |
|content     | content     | yes      | object | Adaptive card object formatted in JSON. For Samples and Templates, see https://adaptivecards.io/samples. |

**Request Body Example**
```json
{
       "type":"message",
       "attachments":[
          {
             "contentType":"application/vnd.microsoft.card.adaptive",
             "contentUrl":null,
             "content":{
                "$schema":"http://adaptivecards.io/schemas/adaptive-card.json",
                "type":"AdaptiveCard",
                "version":"1.2",
                "body":[
                    {
                    "type": "TextBlock",
                    "text": "For Samples and Templates, see [https://adaptivecards.io/samples](https://adaptivecards.io/samples)"
                    }
                ]
             }
          }
       ]
    }
```

The properties for Adaptive Card JSON file are as follows:
* The `"type"` field must be `"message"`.
* The `"attachments"` array contains a set of card objects.
* The `"contentType"` field must be set to Adaptive Card type.
* The `"content"` object is the card formatted in JSON.


## Como Configurar um Webhook no Microsoft Teams
### Pré-requisitos

| Requisito            | Descrição                                                                                              |
|:--------------------:|:------------------------------------------------------------------------------------------------------:|
| Python               | Linguagem de programação usada para desenvolver o script do webhook.                                   |
| Visual Studio Code   | Ambiente de desenvolvimento integrado (IDE) para escrever, testar e executar scripts em Python.        |
| Bibliotecas Python   | Bibliotecas como requests para fazer requisições HTTP ao Teams. (Instalar via `pip install requests`). |
| Conta Microsoft 365  | Acesso a uma conta Microsoft 365 com permissões adequadas para configurar webhooks no Microsoft Teams. |
| Microsoft Teams      | Aplicativo de colaboração necessário para configurar e testar o webhook.                               |
| Microsoft Teams Chat | Canal ou chat onde o webhook será configurado para enviar notificações.                                |

## Passos para Criar o Webhook
### Passo 1: Criando o Webhook

Atualmente, existem duas formas de gerar um webhook no Microsoft Teams:
* Através dos Conectores do Microsoft 365 (Incoming Webhook), que serão desativados em breve, motivo pelo qual não abordaremos essa opção neste tutorial.
* Através do Microsoft Workflows, método que será abordado utilizaremos nesse tutorial.

Para mais informações sobre a descontinuação dos Conectores do Microsoft 365, acesse o link oficial: [Retirement of Office 365 connectors within Microsoft Teams](https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/).

Para a criação Inbound Webhooks através workflows utilizando o teams Existem duas maneiras de fazer um Inbound Webhooks. 
Para publicar automaticamente num chat ou canal quando um pedido de webhook é recebido

Via templates ou do zero 

dentro da página inicial do teams workflows (representada abaxio) observamos as duas opções de criação de um webhook.  

{{<figure class="post_image" src="../images/pagina_inicial_0.png">}}

Inciciando com um a construção de webhook através de templates teams opção 1.
Nessa pagina podemos observar dirsos templates disponibilizados pelo teams que depois podemos cutomizar. como Agendar uma resposta, Acompanhar uma mensagem, Salvar mensgem no OneNote entre outros modelos, Postar em um chat quando uma solicitação de webhook for recebida, Postar em um canal quando uma solicitação de webhook for recebida, analisar sentimento de emails com AI Builder, Notificar um equipe quando o Planner alterar o status de tarefas, entre outros modelos. utilize os modelos de fluxo de trabalho predefinidos.
Para nosso problema vamos selecionar essa opção "Postar em um chat quando uma solicitação de webhook for recebida" Abaixo observamos o modelo escolhido.

{{<figure class="post_image" src="../images/template_0.png">}}

Após selecionar a opção desejada de modelo de template, vai abrir a tela de criação de um novo fluxo. Nela selecionamos o nome do nosso fluxo. nosso caso vamos selecionar "Webhook test". Após isso clicamos em avançar. Abaixo observamos a tela descrita.

{{<figure class="post_image" src="../images/template_1.png">}}

Após a criação do fluxo, o teams vai nos retornar que o fluxo de trabalho foi adicionado com sucesso e junto vai nos dar nossa URL para nosso novo webhook. Abaixo temos um exemplo do passo. Nosso novo webhook já está criado e pronto para utilização.

{{<figure class="post_image" src="../images/template_2.png">}}

Opção 2, criando um fluxo de trabalho do zero.
Nesse opção selecionamos a opção de criar do zero em que montamos passo a passo o fluxo de trabalho que será executado dentro da infraestrura da microsoft do incio com o trigger até as subsequtens passos de pre-processamento e ações como posts, criarção de cards entre outros.  Após clicar na opção criar do zero somos apresentados com a forma inicial do fluxo, com o a criação do gatilho. nessa tela somos apresentados com diversos gatilhos.

{{<figure class="post_image" src="../images/criacao_zero_0.png">}}

No nosso projeto queremos o gatilho de quando um webhook é recebido devemos tomar uma ação. Para isso preciamos selecionar a opção Quando uma solicitação de webhook do Teams é recebeda. Abaixo temos um print da opção a ser selecionada.

{{<figure class="post_image" src="../images/criacao_zero_1.png">}}

Após isso, nosso fluxo nos disponibiliza a URL do webhook (URL DE HTTP POST) a qual vamos utilizar para acionar esse fluxo. Após a criação desse trigger, vamos criar uma ação a ser executada após o recebimento desse webhook, neste caso selecionamos "Send each adaptive card"  combinado com Post card in a chat or channel. Simplificadamente estamos criando um "for" para percorrer os body.attachemnts do conteudo do Post e enviar uma mensagem com o conteudo content para o chat Teams para cada um.

{{<figure class="post_image" src="../images/criacao_zero_2.png">}}

É imporante resaltar que ambas opções de construção desse webhook resultam em fluxos identicos.

Com os webhooks criados devemos observar algo assim na página de fluxos de trabalho.

{{<figure class="post_image" src="../images/webhook_completo.png">}}

### Passo 2: Testando o Webhook

Para testar nosso novo webhook no Microsoft teams, criei o seguinte script python, que envia um request POST através da lib requests do python. Nesse script apenas enviamos uma mensagem no formato AdaptiveCard para testar que nosso webhook está


```python
from requests import post
WEBHOOK_URL="https://brazilsouth.logic.azure.com:443/workflows/XXX"


alerts_body = {
     "type": "AdaptiveCard",
     "msteams": {
       "width": "Full"
     },
     "body": [
       {
         "type": "Container",
         "items": [
           {
             "type": "TextBlock",
             "text": "Testing Teams Workflow"
           }
         ]
       }
     ]
   }

teams_message = {
           "type": "message",
           "attachments": [
               {
                   "contentType": "application/vnd.microsoft.card.adaptive",
                   "content": alerts_body
               }
           ],
       }

response = post(
   WEBHOOK_URL,
   json=teams_message,
   headers={"Content-Type": "application/json"},
   timeout=30,
)

```

Abaixo, podemos ver que o script foi executado com sucesso, a mensagem foi recebida no chat e a imagem foi exibida corretamente.

{{<figure class="post_image" src="../images/testing_webhook_teams.png">}}

## Conclusão

Como vimos, configurar um webhook no Microsoft Teams é uma tarefa simples e eficaz para automatizar a comunicação em tempo real. Com apenas alguns passos, podemos integrar sistemas externos ao Teams, garantindo que as notificações críticas sejam enviadas diretamente para o canal ou chat desejado, sem a necessidade de intervenções manuais.

Em resumo, essa solução não só resolve o problema de forma rápida e eficiente, como também facilita a automação da comunicação, deixando a sua equipe mais conectada e pronta para responder aos desafios de forma mais eficaz.


Fontes:
* https://mailchimp.com/pt-br/marketing-glossary/webhook/
* https://learn.microsoft.com/pt-br/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
* https://learn.microsoft.com/pt-br/connectors/teams/
* https://support.microsoft.com/en-us/office/create-incoming-webhooks-with-workflows-for-microsoft-teams-8ae491c7-0394-4861-ba59-055e33f75498
* https://adaptivecards.io/designer/