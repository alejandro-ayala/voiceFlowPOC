# 🚀 QUICK START GUIDE - VoiceFlow STT Agent

## ⚡ 5-Minute Setup

### 1. Dependencies
```bash
py -m pip install -r requirements.txt
```

### 2. Configuration
```bash
copy .env.example .env
# Edit .env with your Azure Speech Services credentials:
# AZURE_SPEECH_KEY=your_key_here
# AZURE_SPEECH_REGION=italynorth
```

### 3. Test System
```bash
# Test Azure connection
py test_azure_connection.py

# Run complete workflow
py main.py
```

## 🎯 Main Entry Points

### Primary Workflow
```bash
py main.py
```
**What it does**: Complete voice workflow (record Spanish audio → transcribe → multi-agent processing)

### Testing Scripts
```bash
py test_full_workflow.py    # Test with pre-recorded audio
py test_azure_connection.py # Verify Azure connectivity
py test_complete.py         # STT transcription test
```

## 📋 Current System Capabilities

- ✅ **Records Spanish voice** from microphone
- ✅ **Transcribes with Azure STT** (es-ES language)
- ✅ **Processes through multi-agent system** (simulated)
- ✅ **Generates accessibility recommendations**
- ✅ **Handles errors gracefully**
- ✅ **Supports multiple STT services** (Azure, Whisper)

## 🔧 Architecture Quick Reference

```
main.py → VoiceflowSTTAgent → STTServiceFactory → AzureSpeechService
    ↓
AccessibleTourismMultiAgent → NLU + Accessibility + Planning
    ↓
Recommendations Output
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `main.py` | 🎯 Main workflow entry point |
| `src/voiceflow_stt_agent.py` | Core STT agent class |
| `src/factory.py` | Service factory (SOLID pattern) |
| `src/services/azure_speech_service.py` | Azure integration |
| `.env` | Configuration (Azure credentials) |

## 🐛 Common Issues & Solutions

### Import Errors
```python
# If you see import errors, check Python path
import sys
sys.path.append('src')
```

### Azure Connection Issues
- Check `.env` file exists and has correct credentials
- Verify region is `italynorth` (for student accounts)
- Test with `py test_azure_connection.py`

### Audio Recording Issues
- Ensure microphone permissions are granted
- Check microphone is not used by other applications
- Verify `sounddevice` and `scipy` are installed

## 🎯 Example Usage

### Record and Process Spanish Audio
```python
# Run main.py and speak in Spanish:
# "Necesito una ruta accesible al museo"
# 
# System will:
# 1. Record your voice
# 2. Transcribe to text
# 3. Process through multi-agent system
# 4. Generate accessibility recommendations
```

### Test with Pre-recorded Audio
```python
# Use existing test audio
py test_full_workflow.py
```

## 🚀 Development Next Steps

### Immediate (Easy wins)
1. **Enhanced NLU**: Replace keyword matching with ML models
2. **Real Tourism APIs**: Connect to actual tourism databases
3. **Better Entity Extraction**: Implement proper NER

### Advanced (Bigger features)
1. **Database Integration**: Persistent conversation history
2. **Web API**: REST endpoints for web/mobile apps
3. **Multi-language**: Add English, French, etc.

## 📚 Documentation

- **[HANDOVER.md](HANDOVER.md)** - Complete project handover
- **[CURRENT_STATUS.md](CURRENT_STATUS.md)** - Current system status
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture
- **[API_REFERENCE.md](API_REFERENCE.md)** - API documentation

---

**System Status**: ✅ FULLY OPERATIONAL  
**Last Tested**: November 27, 2025  
**Ready For**: Production development or feature expansion
