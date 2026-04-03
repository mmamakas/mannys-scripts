# Huntress Onboarding Scripts

PowerShell scripts for deploying and configuring Huntress EDR on Windows systems.

## Scripts

### Enable-HuntressAuditPolicy.ps1

Configures Windows Advanced Audit Policy to match Huntress recommendations for optimal EDR coverage.

**What it does:**
- Enables all recommended audit categories (Account Logon, Account Management, Logon/Logoff, etc.)
- Disables noisy/unnecessary events to reduce log bloat
- Intentionally leaves Process Creation/Termination disabled (Huntress EDR handles this)

**Usage:**
```powershell
# Run as Administrator
.\Enable-HuntressAuditPolicy.ps1
```

**Requirements:**
- Windows Server 2012 R2+ or Windows 10+
- Administrator privileges
- PowerShell 5.1+

**Reference:**
- [Huntress Audit Policy Documentation](https://support.huntress.io/hc/en-us/articles/49363914702867-Enforcing-Windows-Logging-Audit-Policies)

**Deployment:**
- Can be deployed via GPO, RMM, or manual execution
- Safe to run multiple times (idempotent)
- Changes take effect immediately

## License

MIT
