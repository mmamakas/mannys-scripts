# Enable-HuntressAuditPolicy.ps1
# Configures Windows Advanced Audit Policy per Huntress recommendations
# https://support.huntress.io/hc/en-us/articles/49363914702867
# Updated 2026-04-10: Added Audit Security Group Management Failure, Detailed File Share Success, Other Policy Change Events Success, Sensitive Privilege Use Failure

#Requires -RunAsAdministrator

Write-Host "Configuring Windows Advanced Audit Policy per Huntress recommendations..." -ForegroundColor Cyan

# Account Logon
Write-Host "`n[Account Logon]" -ForegroundColor Yellow
auditpol /set /subcategory:"Credential Validation" /success:enable /failure:enable
auditpol /set /subcategory:"Kerberos Authentication Service" /success:enable /failure:enable
auditpol /set /subcategory:"Kerberos Service Ticket Operations" /success:enable /failure:enable
auditpol /set /subcategory:"Other Account Logon Events" /success:disable /failure:disable

# Account Management
Write-Host "[Account Management]" -ForegroundColor Yellow
auditpol /set /subcategory:"Application Group Management" /success:disable /failure:disable
auditpol /set /subcategory:"Computer Account Management" /success:enable /failure:enable
auditpol /set /subcategory:"Distribution Group Management" /success:enable /failure:enable
auditpol /set /subcategory:"Other Account Management Events" /success:enable /failure:disable
auditpol /set /subcategory:"Security Group Management" /success:enable /failure:enable
auditpol /set /subcategory:"User Account Management" /success:enable /failure:enable

# Detailed Tracking
Write-Host "[Detailed Tracking]" -ForegroundColor Yellow
auditpol /set /subcategory:"DPAPI Activity" /success:disable /failure:disable
auditpol /set /subcategory:"Plug and Play Events" /success:enable /failure:disable
auditpol /set /subcategory:"Process Creation" /success:disable /failure:disable
auditpol /set /subcategory:"Process Termination" /success:disable /failure:disable
auditpol /set /subcategory:"RPC Events" /success:disable /failure:disable
auditpol /set /subcategory:"Token Right Adjusted Events" /success:disable /failure:disable

# DS Access (Domain Controllers only)
Write-Host "[DS Access]" -ForegroundColor Yellow
auditpol /set /subcategory:"Detailed Directory Service Replication" /success:disable /failure:disable
auditpol /set /subcategory:"Directory Service Access" /success:enable /failure:enable
auditpol /set /subcategory:"Directory Service Changes" /success:enable /failure:disable
auditpol /set /subcategory:"Directory Service Replication" /success:disable /failure:disable

# Logon/Logoff
Write-Host "[Logon/Logoff]" -ForegroundColor Yellow
auditpol /set /subcategory:"Account Lockout" /success:disable /failure:enable
auditpol /set /subcategory:"User / Device Claims" /success:disable /failure:disable
auditpol /set /subcategory:"Group Membership" /success:disable /failure:disable
auditpol /set /subcategory:"IPsec Extended Mode" /success:disable /failure:disable
auditpol /set /subcategory:"IPsec Main Mode" /success:disable /failure:disable
auditpol /set /subcategory:"IPsec Quick Mode" /success:disable /failure:disable
auditpol /set /subcategory:"Logoff" /success:enable /failure:disable
auditpol /set /subcategory:"Logon" /success:enable /failure:enable
auditpol /set /subcategory:"Network Policy Server" /success:enable /failure:enable
auditpol /set /subcategory:"Other Logon/Logoff Events" /success:enable /failure:enable
auditpol /set /subcategory:"Special Logon" /success:enable /failure:disable

# Object Access
Write-Host "[Object Access]" -ForegroundColor Yellow
auditpol /set /subcategory:"Application Generated" /success:disable /failure:disable
auditpol /set /subcategory:"Certification Services" /success:disable /failure:disable
auditpol /set /subcategory:"Detailed File Share" /success:enable /failure:enable
auditpol /set /subcategory:"File Share" /success:enable /failure:enable
auditpol /set /subcategory:"File System" /success:disable /failure:disable
auditpol /set /subcategory:"Filtering Platform Connection" /success:disable /failure:enable
auditpol /set /subcategory:"Filtering Platform Packet Drop" /success:disable /failure:disable
auditpol /set /subcategory:"Handle Manipulation" /success:disable /failure:disable
auditpol /set /subcategory:"Kernel Object" /success:enable /failure:enable
auditpol /set /subcategory:"Other Object Access Events" /success:enable /failure:enable
auditpol /set /subcategory:"Registry" /success:disable /failure:disable
auditpol /set /subcategory:"Removable Storage" /success:enable /failure:enable
auditpol /set /subcategory:"SAM" /success:disable /failure:disable
auditpol /set /subcategory:"Central Policy Staging" /success:disable /failure:disable

# Policy Change
Write-Host "[Policy Change]" -ForegroundColor Yellow
auditpol /set /subcategory:"Audit Policy Change" /success:enable /failure:disable
auditpol /set /subcategory:"Authentication Policy Change" /success:enable /failure:disable
auditpol /set /subcategory:"Authorization Policy Change" /success:enable /failure:disable
auditpol /set /subcategory:"Filtering Platform Policy Change" /success:enable /failure:disable
auditpol /set /subcategory:"MPSSVC Rule-Level Policy Change" /success:enable /failure:enable
auditpol /set /subcategory:"Other Policy Change Events" /success:enable /failure:enable

# Privilege Use
Write-Host "[Privilege Use]" -ForegroundColor Yellow
auditpol /set /subcategory:"Non Sensitive Privilege Use" /success:disable /failure:disable
auditpol /set /subcategory:"Other Privilege Use Events" /success:disable /failure:disable
auditpol /set /subcategory:"Sensitive Privilege Use" /success:enable /failure:enable

# System
Write-Host "[System]" -ForegroundColor Yellow
auditpol /set /subcategory:"IPsec Driver" /success:disable /failure:disable
auditpol /set /subcategory:"Other System Events" /success:enable /failure:enable
auditpol /set /subcategory:"Security State Change" /success:enable /failure:disable
auditpol /set /subcategory:"Security System Extension" /success:enable /failure:disable
auditpol /set /subcategory:"System Integrity" /success:enable /failure:enable

Write-Host "`n✓ Huntress Advanced Audit Policy configured successfully!" -ForegroundColor Green
Write-Host "`nCurrent audit policy:" -ForegroundColor Cyan
auditpol /get /category:*

Write-Host "`nNOTE: If using Huntress EDR, Process Creation and Process Termination are intentionally disabled." -ForegroundColor Yellow
Write-Host "If NOT using Huntress EDR, enable Process Creation manually:" -ForegroundColor Yellow
Write-Host "  auditpol /set /subcategory:`"Process Creation`" /success:enable" -ForegroundColor Gray
