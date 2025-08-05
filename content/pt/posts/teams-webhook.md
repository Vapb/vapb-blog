---
title: Configurando um Webhook no Microsoft Teams
author: "vapb"
description: Um breve tutorial com exemplo prático para configurar e testar um webhook no Microsoft Teams.
date: 2025-01-17
tags: ["microsoft-teams", "python"]
toc: true
---

## Introdução

Imagine que o seu sistema está funcionando normalmente, quando, de repente, ocorre um evento crítico. Nesse momento, torna-se essencial notificar imediatamente sua equipe e as partes envolvidas. Em vez de depender de e-mails ou atualizações manuais, você pode automatizar o envio de alertas em tempo real diretamente para um canal do Microsoft Teams. Essa abordagem garante que sua equipe receba as informações rapidamente e possa agir de forma imediata, minimizando o impacto do incidente.

Em sistemas dinâmicos, a comunicação eficiente é vital para a operação. Enviar notificações diretamente aos stakeholders e à equipe é uma maneira prática de manter todos informados. Neste post, vamos mostrar como configurar um webhook no Microsoft Teams para tornar esse processo ainda mais ágil.


## O Que São Webhooks?

Um webhook, por definição, é uma forma de comunicação leve e orientada a eventos, que envia dados automaticamente entre aplicações via HTTP, sem a necessidade de consultas contínuas (polling). Em outras palavras, é um método que permite a um sistema fornecer informações em tempo real a outros sistemas, possibilitando que um aplicativo envie uma notificação para outro quando um evento específico ocorre.

Sem me aprofundar muito no conceito de webhook e seus detalhes, podemos resumir o processo da seguinte forma: existem dois sistemas principais envolvidos — o **Sender** (Aplicação de Origem), que envia a notificação quando um evento acontece, e o **Receiver** (Aplicação de Destino), que é o sistema responsável por receber os dados enviados pelo webhook.

O fluxo de funcionamento de um webhook geralmente segue estes passos::
* O **Receiver**  registra uma URL pública para onde deseja receber os dados, conhecida como endpoint.
* O **Sender**  é configurado para enviar uma mensagem HTTP (geralmente um POST) para essa URL sempre que um evento específico ocorre.
* O **Receiver** processa os dados recebidos e executa as ações necessárias.


## Webhooks no Microsoft Teams

Um webhook no Microsoft Teams é um mecanismo que permite a integração de sistemas externos com canais do Teams. Ele atua como um ponto de entrada, recebendo mensagens de outros serviços ou aplicativos e exibindo-as diretamente em um canal do Teams, proporcionando atualizações em tempo real.

Existem dois tipos de webhooks no Microsoft Teams:
* **Inbound Webhooks (Webhooks de Entrada)**: Usados para receber mensagens de sistemas externos. Nesse caso, um serviço envia uma requisição HTTP POST para a URL do webhook configurado no Teams, e a mensagem é processada e exibida no canal correspondente.
* **Outgoing Webhooks (Webhooks de Saída)**: Usados para enviar mensagens do Teams para um serviço externo.

Neste tutorial, vamos focar nos **Inbound Webhooks (Webhooks de Entrada)**, pois o objetivo é configurar um sistema capaz de enviar mensagens para um chat ou canal do Teams, notificando as partes interessadas sobre eventos críticos que ocorrem no sistema.

**TeamsIncomingWebhookTrigger** Esse trigger permite iniciar um fluxo ao receber uma requisição POST enviada para o endpoint exposto pelo webhook. Você pode incluir um array de adaptive cards no corpo da requisição, que serão utilizados para definir ações subsequentes no fluxo. Vale destacar que esse trigger suporta apenas requisições POST, não sendo compatível com requisições GET.

Abaixo está o esquema do corpo da requisição (Request Body Schema).

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
### Criando o Webhook

Atualmente, existem duas formas de gerar um webhook no Microsoft Teams:
* Através dos Conectores do Microsoft 365 (Incoming Webhook): Essa opção será desativada em breve, motivo pelo qual não será abordada neste tutorial.
* Através do Microsoft Workflows: Este é o método que utilizaremos neste tutorial.

Para mais informações sobre a descontinuação dos Conectores do Microsoft 365, acesse o link oficial: [Retirement of Office 365 connectors within Microsoft Teams](https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/).

Existem duas formas de criar um Inbound Webhook para publicar automaticamente em um chat ou canal do Teams quando um pedido de webhook é recebido:
* Via templates (modelos prontos)
* Do zero (personalizado)

Na página inicial do Microsoft Workflows (imagem abaixo), você encontrará as duas opções disponíveis para configurar um webhook.

{{<figure class="post_image" src="../images/webhook_teams/pagina_inicial_0.png">}}

#### Templates (Opção 1)
Iniciando a construção de um webhook utilizando templates do Teams (opção 1):
Para iniciar a construção de um webhook utilizando templates no Teams, você será apresentado a uma página com diversos modelos prontos para uso. Esses templates foram criados para facilitar a integração com diferentes funcionalidades e podem ser personalizados de acordo com as necessidades específicas. Entre os exemplos disponíveis, encontramos opções como agendar respostas automáticas, acompanhar mensagens, salvar conteúdos no OneNote, postar notificações em chats ou canais quando uma solicitação de webhook é recebida, e até mesmo analisar o sentimento de e-mails utilizando o AI Builder. Além disso, há templates para notificar equipes quando o status de tarefas no Planner é alterado, entre outras possibilidades.

Para resolver o problema em questão, vamos selecionar o template **"Postar em um chat quando uma solicitação de webhook for recebida"**, que atende perfeitamente ao nosso objetivo. Abaixo, você poderá observar o modelo escolhido, que será a base para o nosso fluxo.

{{<figure class="post_image" src="../images/webhook_teams/template_0.png">}}

Após selecionar o modelo de template desejado, será exibida a tela de criação de um novo fluxo. Nessa etapa, você deverá definir o nome do fluxo. No nosso caso, vamos nomeá-lo como "Webhook Test". Em seguida, basta clicar em "Avançar". Abaixo, você pode visualizar a tela descrita.

{{<figure class="post_image" src="../images/webhook_teams/template_1.png">}}

Após a criação do fluxo, o Teams confirmará que o fluxo de trabalho foi adicionado com sucesso e, juntamente com a confirmação, fornecerá a URL do nosso novo webhook. Abaixo, mostramos um exemplo dessa etapa. Com isso, o webhook está criado e pronto para ser utilizado.

{{<figure class="post_image" src="../images/webhook_teams/template_2.png">}}

#### Do zero (Opção 2)
Opção 2, criando um fluxo de trabalho do zero.
Nesta opção, selecionamos a criação do fluxo do zero, permitindo que construamos, passo a passo, o fluxo de trabalho que será executado dentro da infraestrutura da Microsoft. O processo começa com a configuração do trigger (gatilho) inicial e segue com os passos subsequentes, incluindo etapas de pré-processamento e ações como publicação de mensagens, criação de cards, entre outras. Ao clicar na opção "Criar do Zero", somos apresentados à estrutura inicial do fluxo, começando pela criação do gatilho. Nessa etapa, são exibidas diversas opções de gatilhos para seleção.

{{<figure class="post_image" src="../images/webhook_teams/criacao_zero_0.png">}}

No nosso projeto, queremos configurar um gatilho que execute uma ação sempre que um webhook for recebido. Para isso, precisamos selecionar a opção "Quando uma solicitação de webhook do Teams é recebida". Abaixo, incluímos uma captura de tela mostrando a opção que deve ser selecionada.

{{<figure class="post_image" src="../images/webhook_teams/criacao_zero_1.png">}}

Após essa etapa, o fluxo fornecerá a URL do webhook (URL de HTTP POST), que será usada para acionar o fluxo. Com o gatilho configurado, o próximo passo é criar a ação a ser executada quando o webhook for recebido. Nesse caso, selecionamos as opções **"Send each adaptive card"** combinada com **"Post card in a chat or channel"**. De forma simplificada, estamos criando um laço for para iterar sobre os `body.attachments` do conteúdo recebido no webhook. Para cada item, o fluxo enviará uma mensagem com o valor de `content` ao chat do Teams.

{{<figure class="post_image" src="../images/webhook_teams/criacao_zero_2.png">}}

É importante ressaltar que ambas as opções de construção do webhook resultam em fluxos idênticos.

Com os webhooks criados, você deverá visualizar algo semelhante na página de fluxos de trabalho.

{{<figure class="post_image" src="../images/webhook_teams/webhook_completo.png">}}

### Testando o Webhook

Para testar nosso novo webhook no Microsoft Teams, criei o seguinte script em Python, que envia uma requisição POST utilizando a biblioteca `requests` do Python. Neste script, enviamos uma mensagem no formato AdaptiveCard para verificar se o webhook está funcionando corretamente.

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

{{<figure class="post_image" src="../images/webhook_teams/testing_webhook_teams.png">}}

## Conclusão

Como vimos, configurar um webhook no Microsoft Teams é uma tarefa simples e eficaz para automatizar a comunicação em tempo real. Com apenas alguns passos, podemos integrar sistemas externos ao Teams, garantindo que as notificações críticas sejam enviadas diretamente para o canal ou chat desejado, sem a necessidade de intervenções manuais.

Em resumo, essa solução não só resolve o problema de forma rápida e eficiente, como também facilita a automação da comunicação, deixando a sua equipe mais conectada e pronta para responder aos desafios de forma mais eficaz.


Fontes:
* https://mailchimp.com/pt-br/marketing-glossary/webhook/
* https://learn.microsoft.com/pt-br/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
* https://learn.microsoft.com/pt-br/connectors/teams/
* https://support.microsoft.com/en-us/office/create-incoming-webhooks-with-workflows-for-microsoft-teams-8ae491c7-0394-4861-ba59-055e33f75498
* https://adaptivecards.io/designer/