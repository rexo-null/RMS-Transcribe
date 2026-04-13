# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.2   | :white_check_mark: |
| 1.0.1   | :x:                |
| 1.0.0   | :x:                |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**⚠️ IMPORTANT: Do NOT create public issues for security vulnerabilities!**

If you discover a security vulnerability within RMS Transcribe, please report it responsibly:

1. **Email**: Send details to [security@rms-company.ru] (or internal IT security team)
2. **Subject**: Use format `[SECURITY] Brief description`
3. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

| Phase | Timeline |
|-------|----------|
| Acknowledgment | Within 48 hours |
| Initial Assessment | Within 5 days |
| Fix Development | Within 30 days |
| Public Disclosure | After fix release |

## Security Measures in Place

- No cloud dependencies - all processing is local
- No telemetry or data collection
- ML models downloaded from trusted sources (Hugging Face)
- No hardcoded secrets in source code
- `.env` file for sensitive configuration

## Best Practices for Users

1. Keep Hugging Face token secure and rotate periodically
2. Use strong access controls for transcription results
3. Keep the application updated to latest version
4. Review `results/` directory access permissions

## Security-related Configuration

```env
# Minimum required in .env
HUGGING_FACE_TOKEN=your_secure_token_here

# Optional security settings
LOG_LEVEL=INFO  # Avoid DEBUG in production
```

---

**Last updated**: 2025-04-10
