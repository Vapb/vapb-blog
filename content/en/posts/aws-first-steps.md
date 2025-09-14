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

{{< hint warning >}}
**⚠️ Important**  
Once an email is associated with an AWS account, it cannot be reused even if the account is closed. Plan accordingly when creating your AWS account.
{{< /hint >}}

### 2.1. Solutions

| Solution | Description | Recommendation |
|----------|-------------|----------------|
| **Different email** | Use a completely different email address | Simple but requires multiple emails |
| **Reactivate old account** | Contact [AWS Support](https://console.aws.amazon.com/support/home) | Best if you had a previous account |
| **Email aliases** | Use Gmail/Outlook aliases | **Recommended** |

{{< details title="📧 Email Aliases Explained" >}}
Add `+alias` to your email. AWS treats it as a different address, but you receive everything in the same inbox:

- `youremail+aws@gmail.com`
- `youremail+test@gmail.com` 
- `youremail+dev@gmail.com`

This works with most email providers including Gmail, Outlook, and others.
{{< /details >}}

## 3. Creating AWS Account

### 3.1. Prerequisites

| Requirement | Description |
|-------------|-------------|
| **Valid Email** | Email address not previously used with AWS |
| **Phone Number** | For account verification |
| **Credit Card** | Required even for Free Tier usage |
| **Valid Address** | Billing and contact information |

### 3.2. Account Creation Steps

{{< details title="📋 Step-by-Step Account Creation" >}}
1. **Access** the AWS account creation page
2. **Fill in the data:**
   - **Root user email**: Main account email
   - **AWS account name**: Account identifier name
   - **Password**: Choose a strong password for the root account
   - **Contact information**: Name, phone, address
   - **Payment method**: Credit card required (even on Free Tier)
   - **Support plan**: Basic Support (free)
3. **Confirm** and finalize registration
{{< /details >}}

{{<figure class="post_image" src="../images/aws-first-steps/01_create_aws_ac.png">}}

## 4. MFA for Root User

To add an extra layer of protection to your AWS root account, Amazon recommends enabling Multi-Factor Authentication (MFA). This significantly improves account security.

{{< hint danger >}}
**🔒 Security Critical**  
Enabling MFA for your root user is **mandatory** for production environments. This protects against unauthorized access even if your password is compromised.
{{< /hint >}}

{{<figure class="post_image" src="../images/aws-first-steps/02_create_aws_ac.png">}}

### 4.1. MFA Device Options

| MFA Type | Security Level | Recommendation |
|----------|---------------|----------------|
| **Authenticator App** | 🟢 High | **Recommended** |
| **Security Key** | 🟢 Very High | Great for high-security needs |
| **Hardware TOTP Token** | 🟢 High | Good but less convenient |

{{< details title="📱 Recommended Authenticator Apps" >}}
- **Google Authenticator** (Free, widely supported)
- **Microsoft Authenticator** (Free, cloud backup)
- **Authy** (Free, multi-device sync)
- **1Password** (Paid, integrated password manager)
{{< /details >}}

{{<figure class="post_image" src="../images/aws-first-steps/03_create_aws_ac.png">}}

## 5. Admin User

After setting up MFA for the root user, create an **Admin user**. The root user should **only be used in critical situations** it's recommended to use an IAM user with administrative permissions for day-to-day account management.

{{< hint warning >}}
**👑 Root User Best Practice**  
Never use the root user for daily operations. Create an admin user instead and reserve root access only for critical account-level tasks.
{{< /hint >}}

### 5.1. Creating the Admin User

In IAM, click **"Create user"** to start.

{{<figure class="post_image" src="../images/aws-first-steps/04_create_aws_ac.png">}}

{{< details title="🔐 When to Use Root vs Admin User" >}}
**Root User Only For:**
- Changing account settings
- Closing your AWS account
- Restoring IAM user permissions
- Changing AWS support plan

**Admin User For:**
- Daily AWS operations
- Creating resources
- Managing services
- Everything else
{{< /details >}}

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

{{< hint info >}}
**🔐 Security Best Practice**  
For other users or teams, follow the **Least Privilege Principle** and assign more granular permissions. Only the admin user should have full access.
{{< /hint >}}

{{<figure class="post_image" src="../images/aws-first-steps/06_create_aws_ac.png">}}

{{< details title="📋 Common IAM Policies for Different Roles" >}}
| Role | Policy | Use Case |
|------|--------|----------|
| **Developer** | `PowerUserAccess` | Most services except IAM |
| **Read-Only** | `ReadOnlyAccess` | Auditing and monitoring |
| **Billing** | `Billing` | Cost management only |
| **EC2 Admin** | `AmazonEC2FullAccess` | EC2 instances management |
{{< /details >}}

### 5.3. Review and Create

Review the user details and permissions summary, then click **"Create user"**. Your admin user is now ready to use!

## 6. Billing Alarm

A simple way to **avoid billing surprises** is to create a **billing alarm**. An alert that notifies you when account costs reach a predefined threshold.

{{< hint danger >}}
**💸 Cost Control Critical**  
Setting up billing alarms is essential to prevent unexpected charges. AWS costs can accumulate quickly if resources are left running accidentally.
{{< /hint >}}

### 6.1. Enabling Billing Alerts

{{< details title="📊 Step-by-Step Billing Alert Setup" >}}
1. **Access**: [Billing and Cost Management](https://console.aws.amazon.com/costmanagement/)
2. **Navigate to**: Billing preferences > Alert preferences
3. **Enable**:
   - ✅ CloudWatch billing alerts
   - ✅ AWS Free Tier Alerts
{{< /details >}}

{{<figure class="post_image" src="../images/aws-first-steps/07_create_aws_ac.png">}}

### 6.2. Recommended Thresholds

| Account Type | Suggested Threshold | Purpose |
|--------------|--------------------|---------|
| **Learning/Testing** | $5-10 | Prevent accidental charges |
| **Small Projects** | $25-50 | Early warning for growth |
| **Production** | Based on budget | Percentage of monthly budget |

This activates billing alerts via AWS CloudWatch.

### 6.3. Creating the CloudWatch Alarm

{{< details title="⚙️ CloudWatch Alarm Configuration Steps" >}}
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
{{< /details >}}

{{< hint info >}}
**📧 Email Confirmation Required**  
Don't forget to confirm your email subscription to SNS, or you won't receive the billing alerts!
{{< /hint >}}

## 7. Billing Access for Admin User

When accessing [Billing and Cost Management](https://console.aws.amazon.com/costmanagement/) with the admin user, you may encounter "Access denied" messages.

{{<figure class="post_image" src="../images/aws-first-steps/14_create_aws_ac.png">}}

{{< hint warning >}}
**🚫 Common Issue**  
By default, only the root user can access billing information. You need to explicitly enable this for IAM users.
{{< /hint >}}

### 7.1. Enabling Billing Access

{{< details title="🔓 Step-by-Step Billing Access Configuration" >}}
1. **Login as Root user**
2. **Go to**: Billing and Cost Management > Account
3. **Enable**: "IAM user/role access to billing information"

{{<figure class="post_image" src="../images/aws-first-steps/15_create_aws_ac.png">}}

{{<figure class="post_image" src="../images/aws-first-steps/16_create_aws_ac.png">}}
{{< /details >}}

{{< hint info >}}
**💡 What This Enables**  
This grants admin users permission to access Cost Explorer, billing information, and cost management tools.
{{< /hint >}}

## 8. MFA for Admin User

Now that you can access the account with the Admin user, add **MFA for this user as well**. The process is the same as we did for the Root user.

{{< hint info >}}
**🔐 Double Security**  
Enabling MFA for your admin user provides an additional security layer for daily operations. Use the same authenticator app for convenience.
{{< /hint >}}

{{<figure class="post_image" src="../images/aws-first-steps/09_create_aws_ac.png">}}

{{< details title="📱 MFA Setup Tips" >}}
- Use the same authenticator app as your root user
- Label the account clearly (e.g., "AWS - Admin User")
- Back up your MFA codes securely
- Test the MFA before logging out
{{< /details >}}

## 9. Conclusion

Your AWS account is now configured with initial security best practices:

{{< details title="✅ Security Checklist Completed" >}}
- 🔐 **MFA enabled for root user** - Protects against unauthorized access
- 👤 **Admin user created** - For daily operations with appropriate permissions  
- 🔐 **MFA enabled for admin user** - Secures day-to-day account access
- 💸 **Billing alarm configured** - Prevents unexpected charges
- 📊 **Billing access enabled** - Admin user can monitor costs
{{< /details >}}

{{< hint success >}}
**🚀 Ready to Go!**  
Your AWS account is now secure and ready for production use. Remember to follow the principle of least privilege when adding new users.
{{< /hint >}}

## 10. References

- [AWS Account Setup Best Practices](https://docs.aws.amazon.com/accounts/latest/reference/best-practices.html)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Billing and Cost Management](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/)
- [AWS CloudWatch Billing Alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/monitor_estimated_charges_with_cloudwatch.html)