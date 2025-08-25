---
title: Configurando um Webhook no Microsoft Teams
author: "vapb"
description: Exemplo prático para configurar um webhook no Teams.
date: 2025-01-17
tags: ["microsoft-teams", "python"]
toc: true
---

## Introdução

Quando eventos críticos acontecem no seu sistema, cada minuto conta. Em vez de depender de e-mails ou verificações manuais, você pode automatizar alertas em tempo real diretamente para um canal do **Microsoft Teams**.

Neste post, vamos mostrar como configurar um`webhook no **Microsoft Teams**` para notificar sua equipe automaticamente quando algo importante acontece no sistema, garantindo resposta rápida e minimizando impactos.

## O Que São Webhooks?

Um webhook, por definição, é uma forma de comunicação leve e orientada a eventos, que envia dados automaticamente entre aplicações via HTTP, sem a necessidade de consultas contínuas (polling). Em outras palavras, é um método que permite a um sistema fornecer informações em tempo real a outros sistemas, possibilitando que um aplicativo envie uma notificação para outro quando um evento específico ocorre.

Existem dois sistemas principais envolvidos — o **Sender** (Aplicação de Origem), que envia a notificação quando um evento acontece, e o **Receiver** (Aplicação de Destino), que é o sistema responsável por receber os dados enviados pelo webhook.

O fluxo de funcionamento de um webhook geralmente segue estes passos:
1. O **Receiver** registra uma URL onde quer receber as notificações
2. O **Sender** é configurado para enviar uma mensagem HTTP (geralmente um POST) para essa URL sempre que um evento específico ocorre
3. O **Receiver** processa os dados recebidos e executa as ações necessárias

## Webhooks no Microsoft Teams

Um webhook no **Microsoft Teams** permite integrar sistemas externos com canais do Teams. Ele recebe mensagens de outros serviços e as exibe diretamente no canal, proporcionando atualizações em tempo real.

Existem dois tipos de webhooks no Microsoft Teams:
1. **Inbound Webhooks (Entrada)**: Recebem mensagens de sistemas externos via HTTP POST e exibem no canal do Teams
2. **Outgoing Webhooks (Saída)**: Enviam mensagens do Teams para serviços externos

> Focaremos nos Inbound Webhooks, pois queremos enviar notificações do nosso sistema para o Teams.

**TeamsIncomingWebhookTrigger**:  Esse trigger permite iniciar um fluxo ao receber uma requisição POST enviada para o endpoint exposto pelo webhook. Você pode incluir um array de adaptive cards no corpo da requisição, que serão utilizados para definir ações subsequentes no fluxo. Vale destacar que esse trigger suporta apenas requisições POST, não sendo compatível com requisições GET.

### Estrutura da Requisição

Para enviar mensagens ao Teams via webhook, você precisa estruturar sua requisição seguindo o formato específico do **Microsoft Teams**.

#### Request Body Schema
| Nome        | Campo       | Obrigatório | Tipo   | Descrição                                            |
|:------------|:------------|:-----------:|:------:|:----------------------------------------------------:|
| type        | type        | Sim         | string | Deve sempre ser `"message"`                          |
| attachments | attachments | Sim         | array  | Array de objetos Adaptive Card (veja schema abaixo)  |

#### Adaptive Card Schema
| Nome        | Campo       | Obrigatório | Tipo   | Descrição                                                             |
|:------------|:------------|:-----------:|:------:|:---------------------------------------------------------------------:|
| contentType | contentType | Sim         | string | Deve ser `"application/vnd.microsoft.card.adaptive"`                  |
| contentUrl  | contentUrl  | Sim         | string | Deve sempre ser `null`                                                |
| content     | content     | Sim         | object | Objeto Adaptive Card em formato JSON.https://adaptivecards.io/samples |

#### Exemplo de Requisição
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

**Pontos importantes:**
- O campo `type` deve ser sempre `"message"`
- O array `attachments` pode conter múltiplos cards
- O campo `"contentType"` deve ser definido como o tipo de Cartão Adaptável.
- O objeto `"content"` é o cartão formatado em JSON.

## Como Configurar um Webhook no Microsoft Teams

### Pré-requisitos
| Requisito               | Descrição                                                       |
|:-----------------------:|:---------------------------------------------------------------:|
| **Python**              | Linguagem para desenvolver o script do webhook                  |
| **Bibliotecas Python**  | `requests` para fazer requisições HTTP (`pip install requests`) |
| **Conta Microsoft 365** | Com permissões para configurar webhooks no Teams                |
| **Microsoft Teams**     | Acesso ao canal onde será configurado o webhook                 |

### Métodos de Configuração

Atualmente, existem duas formas de criar um webhook no Microsoft Teams:

1. **Conectores do Microsoft 365** (Deprecated)
   - ⚠️ Esta opção será descontinuada em breve
   - Não recomendado para novos projetos

2. **Microsoft Workflows** (Recomendado)
   - ✅ Método atual e suportado
   - Maior flexibilidade e recursos

> **Nota**: Para mais informações sobre a descontinuação dos Conectores, consulte: [Retirement of Office 365 connectors within Microsoft Teams](https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/)

### Criando o Webhook via Microsoft Workflows

No Microsoft Workflows, você pode criar um Inbound Webhook de duas formas:

1. **Via Templates** - Usar modelos prontos para casos comuns
2. **Do Zero** - Criar um webhook personalizado para suas necessidades

Na página inicial do Microsoft Workflows, você encontrará ambas as opções disponíveis para configurar seu webhook.

{{<figure class="post_image" src="../images/webhook_teams/pagina_inicial_0.png">}}

#### Opção 1: Usando Templates

Os templates do Teams oferecem modelos prontos para diferentes cenários de integração. Você encontrará opções como:

- Agendar respostas automáticas
- Acompanhar mensagens
- Salvar conteúdos no OneNote
- **Postar em chat quando webhook recebido** ✅
- Analisar sentimento de e-mails com AI Builder
- Notificar mudanças de status no Planner

##### Passo 1: Selecionando o Template

Para nosso objetivo, vamos usar o template **"Postar em um chat quando uma solicitação de webhook for recebida"**, que atende perfeitamente nossas necessidades.

{{<figure class="post_image" src="../images/webhook_teams/template_0.png">}}

##### Passo 2: Configurando o Fluxo

Após selecionar o template:
1. Defina um nome para o fluxo (ex: "Webhook Alertas Sistema")
2. Clique em "Avançar" para continuar
3. Configure os parâmetros específicos conforme sua necessidade

{{<figure class="post_image" src="../images/webhook_teams/template_1.png">}}

##### Passo 3: Obtenção da URL

Após criar o fluxo, o Teams:
- ✅ Confirmará que o workflow foi criado com sucesso
- 🔗 Fornecerá a URL única do seu webhook
- ⚡ O webhook estará pronto para uso imediatamente

> **Dica**: Anote a URL fornecida, pois ela será necessária para fazer as requisições do seu sistema.

{{<figure class="post_image" src="../images/webhook_teams/template_2.png">}}

#### Opção 2: Criando do Zero

Para maior controle sobre o fluxo, você pode criar um webhook personalizado do zero. Esta opção permite configurar cada etapa manualmente.

##### Passo 1: Configurando o Trigger

1. Clique em "Criar do Zero"
2. Selecione o trigger **"Quando uma solicitação de webhook do Teams é recebida"**
3. O sistema fornecerá automaticamente a URL do webhook (HTTP POST)

{{<figure class="post_image" src="../images/webhook_teams/criacao_zero_1.png">}}

##### Passo 2: Adicionando as Ações

Configure as ações que serão executadas quando o webhook for acionado:
1. **"Send each adaptive card"** - Para iterar sobre os cards recebidos
2. **"Post card in a chat or channel"** - Para enviar mensagens ao Teams

> De forma simplificada, estamos criando um loop for para iterar sobre os `body.attachments` do conteúdo recebido no webhook. Para cada item, o fluxo enviará uma mensagem com o valor de `content` ao chat do Teams.

{{<figure class="post_image" src="../images/webhook_teams/criacao_zero_2.png">}}

##### Passo 3: Finalização

Após configurar trigger e ações:
- ✅ Salve o fluxo
- 🔗 Anote a URL fornecida
- ⚡ Teste a integração

Após criar seus webhooks, você verá todos os fluxos listados na página de workflows do Microsoft Teams, onde poderá gerenciar, editar ou monitorar o status de cada um.

{{<figure class="post_image" src="../images/webhook_teams/webhook_completo.png">}}

> **Importante**: Ambas as opções (Template e Do Zero) resultam em fluxos funcionalmente idênticos. A diferença está no nível de customização durante a criação.

### Testando o Webhook

Para validar se o webhook está funcionando, vamos criar um script Python simples que envia uma mensagem de teste.

### Script de Teste

```python
from requests import post

# Substitua pela URL do seu webhook
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

Configurar um webhook no Microsoft Teams é uma solução simples e poderosa para automatizar notificações em tempo real. Com poucos passos, você pode integrar qualquer sistema externo ao Teams, garantindo que sua equipe receba alertas críticos instantaneamente.

**Principais benefícios:**
- ⚡ **Comunicação instantânea** - Notificações em tempo real
- 🎨 **Formatação rica** - Adaptive Cards com visual profissional  
- 🔧 **Fácil implementação** - Poucos passos para configurar
- 📊 **Monitoramento centralizado** - Todas as notificações em um local
- 🔄 **Automação completa** - Sem intervenção manual necessária

> Esta solução não apenas resolve problemas de comunicação, mas também mantém sua equipe mais conectada e preparada para responder rapidamente a qualquer situação.

## Referências

- [Mailchimp - Webhook Guide](https://mailchimp.com/pt-br/marketing-glossary/webhook/)
- [Microsoft Learn - Incoming Webhooks](https://learn.microsoft.com/pt-br/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook)
- [Microsoft Learn - Teams Connectors](https://learn.microsoft.com/pt-br/connectors/teams/)
- [Microsoft Support - Workflows for Teams](https://support.microsoft.com/en-us/office/create-incoming-webhooks-with-workflows-for-microsoft-teams-8ae491c7-0394-4861-ba59-055e33f75498)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)