---
title: Configuring a Webhook in Microsoft Teams
author: "vapb"
description: Practical example for configuring a webhook in Teams.
date: 2025-01-17
tags: ["microsoft-teams", "python"]
toc: true
---

## 1. Introduction

In this post, we'll show how to configure a webhook in **Microsoft Teams** to automatically notify your team when something important happens in the system, ensuring quick response and minimizing impacts.

## 2. What Are Webhooks?

A webhook, by definition, is a lightweight, event-driven form of communication that automatically sends data between applications via HTTP, without the need for continuous polling. In other words, it's a method that allows one system to provide real-time information to other systems, enabling an application to send a notification to another when a specific event occurs.

There are two main systems involved: 
- **Sender** (Source Application) Sends the notification when an event occurs
- **Receiver** (Destination Application) Receives the data sent by the webhook.

{{< details title="📋 Webhook Workflow" >}}
1. The **Receiver** registers a URL where it wants to receive notifications
2. The **Sender** is configured to send an HTTP message (usually POST) to that URL whenever a specific event occurs
3. The **Receiver** processes the received data and executes the necessary actions
{{< /details >}}


## 3. Webhooks in Microsoft Teams

A webhook in **Microsoft Teams** allows external systems integration with Teams channels. It receives messages from other services and displays them directly in the channel, providing real-time updates.

There are two types of webhooks in Microsoft Teams:
1. **Inbound Webhooks (Incoming)**: Receive messages from external systems via HTTP POST and display them in the Teams channel
2. **Outgoing Webhooks (Outgoing)**: Send messages from Teams to external services

> We'll focus on Inbound Webhooks, as we want to send notifications from our system to Teams.

**TeamsIncomingWebhookTrigger**: This trigger allows initiating a flow when receiving a POST request sent to the endpoint exposed by the webhook. You can include an array of adaptive cards in the request body, which will be used to define subsequent actions in the flow. It's worth noting that this trigger only supports POST requests, not being compatible with GET requests.

### 3.1. Request Structure

To send messages to Teams via webhook, you need to structure your request following the specific **Microsoft Teams** format.

#### 3.1.1. Request Body Schema
| Name        | Field       | Required |  Type  |                    Description                    |
| :---------- | :---------- | :------: | :----: | :-----------------------------------------------: |
| type        | type        |   Yes    | string |            Must always be `"message"`             |
| attachments | attachments |   Yes    | array  | Array of Adaptive Card objects (see schema below) |

#### 3.1.2. Adaptive Card Schema
| Name        | Field       | Required |  Type  |                             Description                              |
| :---------- | :---------- | :------: | :----: | :------------------------------------------------------------------: |
| contentType | contentType |   Yes    | string |         Must be `"application/vnd.microsoft.card.adaptive"`          |
| contentUrl  | contentUrl  |   Yes    | string |                        Must always be `null`                         |
| content     | content     |   Yes    | object | Adaptive Card object in JSON format.https://adaptivecards.io/samples |

#### 3.1.3. Request Example
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

**Important points:**
- The `type` field must always be `"message"`
- The `attachments` array can contain multiple cards
- The `"contentType"` field must be set as the Adaptive Card type.
- The `"content"` object is the card formatted in JSON.

## 4. How to Configure a Webhook in Microsoft Teams

### 4.1. Prerequisites
|        Requirement        |                        Description                         |
| :-----------------------: | :--------------------------------------------------------: |
|        **Python**         |           Language to develop the webhook script           |
|   **Python Libraries**    |   `requests` for HTTP requests (`pip install requests`)    |
| **Microsoft 365 Account** |      With permissions to configure webhooks in Teams       |
|    **Microsoft Teams**    | Access to the channel where the webhook will be configured |

### 4.2. Configuration Methods

Currently, there are two ways to create a webhook in Microsoft Teams:

1. **Microsoft 365 Connectors** (Deprecated) ❌
2. **Microsoft Workflows** (Recommended) ✅

{{< hint warning >}}
**📚 Additional Reading**  
For more information about Connectors deprecation, see: [Retirement of Office 365 connectors within Microsoft Teams](https://devblogs.microsoft.com/microsoft365dev/retirement-of-office-365-connectors-within-microsoft-teams/)
{{< /hint >}}

### 4.3. Creating the Webhook via Microsoft Workflows

In Microsoft Workflows, you can create an Inbound Webhook in two ways:

1. **📋 Via Templates** - Use ready-made templates for common cases
2. **⚙️ From Scratch** - Create a custom webhook for your needs

On the Microsoft Workflows homepage, you'll find both options available to configure your webhook.

{{<figure class="post_image" src="../images/webhook_teams/pagina_inicial_0.png">}}

#### 4.3.1. Using Templates

Teams templates offer ready-made models for different integration scenarios. You'll find options like:

- Schedule automatic responses
- Track messages
- Save content to OneNote
- **Post in chat when webhook received** ✅
- Analyze email sentiment with AI Builder
- Notify Planner task status changes

##### 4.3.1.1. Selecting the Template

For our objective, we'll use the template **"Post in a chat when a webhook request is received"**, which perfectly meets our needs.

{{<figure class="post_image" src="../images/webhook_teams/template_0.png">}}

##### 4.3.1.2. Configuring the Flow

After selecting the template:
1. Define a name for the flow (e.g., "System Alert Webhook")
2. Click "Next" to continue
3. Configure specific parameters according to your needs

{{<figure class="post_image" src="../images/webhook_teams/template_1.png">}}

##### 4.3.1.3. Getting the URL

After creating the flow, Teams will:
- ✅ Confirm that the workflow was created successfully
- 🔗 Provide the unique URL for your webhook
- ⚡ The webhook will be ready for immediate use

> **Tip**: Note down the provided URL, as it will be necessary to make requests from your system.

{{<figure class="post_image" src="../images/webhook_teams/template_2.png">}}

#### 4.3.2. Creating from Scratch

For greater control over the flow, you can create a custom webhook from scratch. This option allows you to manually configure each step.

##### 4.3.2.1. Configuring the Trigger

1. Click "Create from Scratch"
2. Select the trigger **"When a Teams webhook request is received"**
3. The system will automatically provide the webhook URL (HTTP POST)

{{<figure class="post_image" src="../images/webhook_teams/criacao_zero_1.png">}}

##### 4.3.2.2. Adding Actions

Configure the actions that will be executed when the webhook is triggered:
1. **"Send each adaptive card"** - To iterate over received cards
2. **"Post card in a chat or channel"** - To send messages to Teams

> Simply put, we're creating a for loop to iterate over the `body.attachments` of the content received in the webhook. For each item, the flow will send a message with the `content` value to the Teams chat.

{{<figure class="post_image" src="../images/webhook_teams/criacao_zero_2.png">}}

##### 4.3.2.3. Finalization

After configuring trigger and actions:
- ✅ Save the flow
- 🔗 Note down the provided URL
- ⚡ Test the integration

After creating your webhooks, you'll see all flows listed on the Microsoft Teams workflows page, where you can manage, edit, or monitor the status of each one.

{{<figure class="post_image" src="../images/webhook_teams/webhook_completo.png">}}

> **Important**: Both options (Template and From Scratch) result in functionally identical flows. The difference lies in the level of customization during creation.

### 4.4. Testing the Webhook

To validate if the webhook is working, let's create a simple Python script that sends a test message.

### 4.5. Test Script

```python
from requests import post

# Replace with your webhook URL
WEBHOOK_URL="https://brazilsouth.logic.azure.com:443/workflows/XXX"

alerts_body = {
    "type": "AdaptiveCard",
    "msteams": {"width": "Full"},
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

Below, we can see that the script was executed successfully, the message was received in the chat, and the image was displayed correctly.

{{<figure class="post_image" src="../images/webhook_teams/testing_webhook_teams.png">}}

## 5. Conclusion

Configuring a webhook in Microsoft Teams is a simple and powerful solution to automate real-time notifications. With just a few steps, you can integrate any external system with Teams, ensuring your team receives critical alerts instantly.

**Main benefits:**
- ⚡ **Instant communication** - Real-time notifications
- 🎨 **Rich formatting** - Adaptive Cards with professional visuals  
- 🔧 **Easy implementation** - Few steps to configure
- 📊 **Centralized monitoring** - All notifications in one place
- 🔄 **Complete automation** - No manual intervention required

> This solution not only solves communication problems but also keeps your team more connected and prepared to respond quickly to any situation.

## 6. References

- [Mailchimp - Webhook Guide](https://mailchimp.com/marketing-glossary/webhook/)
- [Microsoft Learn - Incoming Webhooks](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook)
- [Microsoft Learn - Teams Connectors](https://learn.microsoft.com/en-us/connectors/teams/)
- [Microsoft Support - Workflows for Teams](https://support.microsoft.com/en-us/office/create-incoming-webhooks-with-workflows-for-microsoft-teams-8ae491c7-0394-4861-ba59-055e33f75498)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)