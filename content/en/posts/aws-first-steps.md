---
title: Initial AWS Setup
author: "vapb"
description: First steps to create and configure an AWS account.
date: 2025-04-19
tags: ["AWS"]
toc: true
---

## 1. Introduction

In this post, we'll create an AWS account and configure the essential points to start using cloud services securely.

## 2. Problem: Email Already Used in AWS

AWS **does not allow reusing an email** that has already been associated with an account, even if it was closed. If you try to use the same address, you'll get an error.

### 2.1. Solutions:

1. **Use a different email**
2. **Try to reactivate the old account** via [AWS Support](https://console.aws.amazon.com/support/home)
3. **Use email aliases** (recommended)

### 2.2. Tip: Email Aliases

Add `+alias` to your email. AWS treats it as a different address, but you receive everything in the same inbox:

- `youremail+aws@gmail.com`
- `youremail+test@gmail.com` 
- `youremail+dev@gmail.com`

## 3. Creating AWS Account

1. **Access** the AWS account creation page
2. **Fill in the data:**
   - **Root user email**: Main account email
   - **AWS account name**: Account identifier name
   - **Password**: Choose a strong password for the root account
   - **Contact information**: Name, phone, address
   - **Payment method**: Credit card required (even on Free Tier)
   - **Support plan**: Basic Support (free)
3. **Confirm** and finalize registration

{{<figure class="post_image" src="../images/aws-first-steps/01_create_aws_ac.png">}}

## 4. MFA for Root User

To add an extra layer of protection to your AWS root account, Amazon recommends enabling Multi-Factor Authentication (MFA). This significantly improves account security.

{{<figure class="post_image" src="../images/aws-first-steps/02_create_aws_ac.png">}}

Choose the type of MFA device you want to use:
- **Authenticator app** (like Google Authenticator) - Recommended
- **Security Key**  
- **Hardware TOTP token**

{{<figure class="post_image" src="../images/aws-first-steps/03_create_aws_ac.png">}}

## 5. Admin User

After setting up MFA for the root user, create an **Admin user**. The root user should **only be used in critical situations** it's recommended to use an IAM user with administrative permissions for day-to-day account management.

In IAM, click **"Create user"** to start.

{{<figure class="post_image" src="../images/aws-first-steps/04_create_aws_ac.png">}}

### 5.1. User Details

- **Username**: Define a name for the user
- **Console access**: Select "Provide user access to the AWS Management Console"
- **User type**: Choose "I want to create an IAM user"
- **Console password**: Choose "Custom password" and **disable** "Users must create a new password at next sign-in"

{{<figure class="post_image" src="../images/aws-first-steps/05_create_aws_ac.png">}}

### 5.2. User Permissions

Configure permissions for the admin user:
- Select **"Attach policies directly"**
- Add the **AdministratorAccess** policy: *"Provides full access to AWS services and resources"*

> **Note**: For other users or teams, follow the **Least Privilege Principle** and assign more granular permissions.

{{<figure class="post_image" src="../images/aws-first-steps/06_create_aws_ac.png">}}

### 5.3. Review and Create

Review the user details and permissions summary, then click **"Create user"**. Your admin user is now ready to use!

## 6. Billing Alarm

A simple way to **avoid billing surprises** is to create a **billing alarm** — an alert that notifies you when account costs reach a predefined threshold.

### 6.1. Enabling Billing Alerts

1. **Access**: [Billing and Cost Management](https://console.aws.amazon.com/costmanagement/)
2. **Navigate to**: Billing preferences > Alert preferences
3. **Enable**:
   - ✅ CloudWatch billing alerts
   - ✅ AWS Free Tier Alerts

{{<figure class="post_image" src="../images/aws-first-steps/07_create_aws_ac.png">}}

This activates billing alerts via AWS CloudWatch.

### 6.2. Creating the CloudWatch Alarm

1. **Access CloudWatch** and go to **Alarms** > **Create Alarm**

{{<figure class="post_image" src="../images/aws-first-steps/10_create_aws_ac.png">}}

2. **Select metric**: Billing > TotalEstimatedCharge

{{<figure class="post_image" src="../images/aws-first-steps/08_create_aws_ac.png">}}

3. **Configure alarm actions**:
   - Set **threshold value** (e.g., $5)
   - Create **SNS topic** for notifications
   - Add your **email** as subscriber

{{<figure class="post_image" src="../images/aws-first-steps/11_create_aws_ac.png">}}

4. **Add name and description** for the alarm

{{<figure class="post_image" src="../images/aws-first-steps/12_create_aws_ac.png">}}

5. **Confirm email subscription** to receive alerts

{{<figure class="post_image" src="../images/aws-first-steps/13_create_aws_ac.png">}}

## 7. Billing Access for Admin User

When accessing [Billing and Cost Management](https://console.aws.amazon.com/costmanagement/) with the admin user, you may encounter "Access denied" messages.

{{<figure class="post_image" src="../images/aws-first-steps/14_create_aws_ac.png">}}

### 7.1. Solution:

1. **Login as Root user**
2. **Go to**: Billing and Cost Management > Account
3. **Enable**: "IAM user/role access to billing information"

{{<figure class="post_image" src="../images/aws-first-steps/15_create_aws_ac.png">}}

{{<figure class="post_image" src="../images/aws-first-steps/16_create_aws_ac.png">}}

> This grants admin users permission to access Cost Explorer and billing information.

## 8. MFA for Admin User

Now that you can access the account with the Admin user, add **MFA for this user as well**. The process is the same as we did for the Root user.

{{<figure class="post_image" src="../images/aws-first-steps/09_create_aws_ac.png">}}

## 9. Conclusion

Your AWS account is now configured with initial security best practices:
- MFA enabled for root user
- Admin user created with appropriate permissions  
- MFA enabled for admin user
- Billing alarm configured to prevent surprises 💸