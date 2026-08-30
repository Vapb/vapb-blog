---
title: Setup Inicial AWS
author: "vapb"
description: Primeiros passos AWS.
date: 2025-04-19
tags: ["aws"]
toc: true
---

## Introdução
Neste pequeno post, vamos passar pelo processo de criação de uma conta na AWS e aproveitar para configurar alguns pontos importantes logo de início.

## AWS, Me deixa voltar!
Há um tempo, criei minha primeira conta na AWS para desenvolver projetos relacionados ao meu MBA em Engenharia de Dados. Após concluir a pós-graduação, notei que a conta continuava gerando custos na nuvem, mesmo com as instâncias desligadas — e como não consegui identificar a origem desses gastos, decidi encerrar a conta para evitar surpresas no cartão 😅.

Mas fica aqui um alerta importante: **a AWS não permite reutilizar um e-mail que já foi associado a uma conta**, mesmo que ela tenha sido encerrada. Ou seja, se você tentar criar uma nova conta usando o mesmo endereço, vai acabar recebendo um erro.

As opções são:
- Criar a nova conta com um e-mail diferente.    
- Tentar reativar a conta antiga (caso ainda não tenha sido encerrada permanentemente), entrando em contato com o [AWS Support](https://console.aws.amazon.com/support/home).

👉 **E se você não quiser criar um novo e-mail só pra isso?**  
Uma solução rápida é utilizar **aliases de e-mail**.

Um alias nada mais é do que adicionar um `+alias` no seu e-mail. A AWS trata como um endereço diferente, mas você continua recebendo tudo normalmente na sua caixa de entrada.

Alguns exemplos:
- `email+awstest@gmail.com`
- `email+devtest@gmail.com`
- `email+tempaws@gmail.com`

Simples, prático e salva tempo. Fica a dica pra quem estiver pensando em encerrar uma conta: pense duas vezes se pretende usá-la novamente no futuro!

## Criando conta na AWS
- Acesse a página de criação de conta da AWS
- Preencha os dados nescessarios:
    * **Root user email address**: Insira o e-mail que será o principal da conta
    * **AWS account name**: Dê um nome para sua conta. Pode ser seu nome, nome da empresa ou qualquer identificação.
    * **Root Password**: A conta "root" é a conta principal da AWS, então escolha uma senha segura.
    * **Informações de contato**: Nome completo, telefone, endereço etc.
    * **Adicione um método de pagamento**: Mesmo usando o **Free Tier**, a AWS exige um cartão de crédito
    * **Escolha o plano de suporte**: o plano **Básico (Basic Support)** já é suficiente e é gratuito
- Confirme e finalize o cadastro.

{{<figure class="post_image" src="../images/aws-first-steps/01_create_aws_ac.png">}}

## MFA para o Usuário Root
Para adicionar uma camada extra de proteção à sua conta root da AWS, a Amazon recomenda habilitar a autenticação multifator (MFA). Isso ajuda a melhorar significativamente a segurança da conta.

{{<figure class="post_image" src="../images/aws-first-steps/02_create_aws_ac.png">}}

Ao configurar, escolha o tipo de dispositivo MFA que deseja usar:
- **Aplicativo autenticador** (como o Google Authenticator)
- **Chave de segurança (Security Key)**
- **Token TOTP de hardware**
    
Pessoalmente, prefiro o uso de aplicativos autenticadores, como o Google Authenticator — são simples, rápidos e confiáveis.

{{<figure class="post_image" src="../images/aws-first-steps/03_create_aws_ac.png">}}


## Usuário Administrador (Admin User)
Após configurar o MFA para o usuário root, o próximo passo é criar um **usuário administrador (Admin)**. Idealmente, o usuário root deve ser utilizado **apenas em situações críticas** — o recomendado é usar um usuário IAM com permissões administrativas para gerenciar a conta no dia a dia.

No IAM clique em **"Criar usuário"** para começar.

{{<figure class="post_image" src="../images/aws-first-steps/04_create_aws_ac.png">}}

### Detalhes do Usuário (User details)
- Defina um nome para o usuário.
- Selecione: **"Provide user access to the AWS Management Console"**.
- Escolha a opção: **"I want to create an IAM user"**.
- Em **Console password**, escolha **"Custom password"** e **desative** a opção _"Users must create a new password at next sign-in"_, já que estamos criando esse usuário para uso próprio.

{{<figure class="post_image" src="../images/aws-first-steps/05_create_aws_ac.png">}}

### Permissões do Usuário (User permissions)
Agora vamos configurar as permissões:
- Selecione a opção de **anexar políticas diretamente (Attach policies directly)** — é mais direto.
- Adicione a política **AdministratorAccess**, cuja descrição é:  
    _"Provides full access to AWS services and resources."_

Essa permissão é adequada porque estamos criando um usuário administrador. Claro que, para outras pessoas ou equipes, o ideal seria seguir o princípio de **menor privilégio (Least Privilege Principle)** e definir permissões mais granulares.

{{<figure class="post_image" src="../images/aws-first-steps/06_create_aws_ac.png">}}

### Revisar e Criar (Review and Create)
Por fim, será exibido um resumo com os detalhes e permissões do novo usuário.  
Revise as informações, clique em **"Create user"** — e pronto! Seu usuário administrador está criado e pronto para uso.


## Billing Alarm
Todos nós já estivemos na posição de subir alguma instância na AWS para um teste rápido… e esquecer de desligá-la. 😅 Aí, semanas depois, chega aquela **continha de 10 dólares** pra lembrar a gente da nuvem.

Uma forma simples de **evitar sustos com cobranças** é criar um **billing alarm** — um alarme que envia um alerta quando os custos da conta atingem um valor pré-definido (threshold).

### Habilitando os Alertas de Cobrança
1. Acesse o link: [Billing and Cost Management](https://console.aws.amazon.com/costmanagement/)
2. Vá em **Billing preferences** > **Alert preferences**
3. Marque as opções:
    - ✅ _CloudWatch billing alerts_
    - ✅ _AWS Free Tier Alerts_

{{<figure class="post_image" src="../images/aws-first-steps/07_create_aws_ac.png">}}
	
Isso ativa os alertas de cobrança pela AWS CloudWatch.

### Criando o Alarme no CloudWatch
Agora, vamos criar o alarme de fato:
1. Acesse o **CloudWatch**
2. Vá em **Alarms** e clique em **Create Alarm**
{{<figure class="post_image" src="../images/aws-first-steps/10_create_aws_ac.png">}}
3. Escolha a métrica:
    - `Billing` > `TotalEstimatedCharge`
{{<figure class="post_image" src="../images/aws-first-steps/08_create_aws_ac.png">}}
4. Configurando Ações do Alarme: Agora vamos configurar o que acontece quando o alarme é ativado:
    - 4.1 Defina um **valor limite** (por exemplo, **5 dólares**).
    - 4.2 Para receber notificações, vamos usar o **SNS (Simple Notification Service)**:
        - 4.2.1. Crie um **tópico** (topic)
        - 4.2.2. Adicione seu **e-mail** como assinante (subscriber)
            {{<figure class="post_image" src="../images/aws-first-steps/11_create_aws_ac.png">}}
    4.2.3. Adicione **nome** e **descrição** para o alarme criados
{{<figure class="post_image" src="../images/aws-first-steps/12_create_aws_ac.png">}}
5. Confirmando o E-mail: Após a criação do alarme, acesse o e-mail que você cadastrou e **confirme a inscrição (subscription)** para começar a receber os alertas.
{{<figure class="post_image" src="../images/aws-first-steps/13_create_aws_ac.png">}}

## Observação
Quando acessamos o link [Billing and Cost Management](https://console.aws.amazon.com/costmanagement/) através do nosso usuário **admin**, nos deparamos com o seguinte cenário: várias mensagens de Access denied – You don’t have permission to Cost Explorer.

{{<figure class="post_image" src="../images/aws-first-steps/14_create_aws_ac.png">}}

Para resolver esse problema, acesse a conta **Root**, vá até Billing and Cost Management > Account e localize a seção "IAM user and role access to billing information". Ative a opção "IAM user/role access to billing information". Isso concederá ao nosso usuário admin permissão para acessar o Cost Explorer, além de visualizar as informações de cobrança (billing information).
{{<figure class="post_image" src="../images/aws-first-steps/15_create_aws_ac.png">}}
{{<figure class="post_image" src="../images/aws-first-steps/16_create_aws_ac.png">}}


## MFA para o Usuário Admin
Agora que acessamos a conta com o usuário Admin, o primeiro passo para torná-la mais segura é **adicionar MFA também para esse usuário**. O processo é o mesmo que fizemos anteriormente para o usuário Root.

{{<figure class="post_image" src="../images/aws-first-steps/09_create_aws_ac.png">}}

## Conclusão
Pronto! Agora sua conta AWS está configurada com as boas práticas iniciais de segurança:
* MFA ativado para o usuário root
* Usuário administrador criado com permissões adequadas
* MFA ativado para o admin
* Alarme de billing configurado para evitar surpresas 💸
