# QDA360 - AI-Assisted Qualitative Analysis

**QDA360** is a Streamlit web application for **AI-assisted qualitative analysis** with a unique **dual-coder verification system**.

## 🎯 Key Features

- **Dual-Coder System**: Two independent LLMs (Gemini 3 Flash & Claude Sonnet 4.5) analyze your data separately, then results are corroborated—mirroring traditional inter-rater reliability practices
- **Transparent Validation**: See where AI coders agree and disagree
- **Full Workflow**: Import → Anonymize → Analyze → Export
- **Privacy-First**: Session-only data, no storage

## 🚀 Quick Start

### Using QDA360 Online

Visit the hosted app: [QDA360 on Streamlit Cloud](https://qda360.streamlit.app) *(deployment link)*

You'll need an **OpenRouter API key** with credits for:
- `google/gemini-3-flash-preview`
- `anthropic/claude-sonnet-4.5`

### Running Locally

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/QDA360.git
cd QDA360

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Download spaCy model for entity detection
python -m spacy download en_core_web_sm

# Run the app
streamlit run app.py
```

## 📦 Supported Formats

| Format | Description |
|--------|-------------|
| DOCX | Word documents with speaker/statement format |
| XLSX | Excel spreadsheets with columns |
| CSV | Comma-separated values |

Expected columns: `speaker`, `statement` (or similar headers)

## 🤖 Dual-Coder System

QDA360's innovation is the **dual-coder verification system**:

```
Interview Data
     │
     ├──────────────────────┐
     ▼                      ▼
🔵 Gemini 3 Flash    🟣 Claude Sonnet 4.5
     │                      │
     └──────────┬───────────┘
               ▼
        Corroboration
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
✅ Consensus  ⚠️ Partial  🔴 Divergent
  (>80%)      (50-80%)    (<50%)
```

### Agreement Levels

- **✅ Consensus (>80%)**: Both coders identified similar findings. High confidence.
- **⚠️ Partial (50-80%)**: Some overlap but differences exist. Review recommended.
- **🔴 Divergent (<50%)**: Significant disagreement. Requires human judgment.

## 📋 Workflow

1. **Upload** - Add interview transcripts (DOCX/XLSX/CSV)
2. **Anonymize** (Optional) - Replace speaker names and detect/mask entities
3. **Analyze** - Dual-coder topic extraction and thematic analysis
4. **Results** - View comparison, resolve differences, export

## 🔒 Privacy

- **No data storage**: All data stays in your browser session
- **Your API key**: Bring your own OpenRouter credentials
- **Local entity detection**: spaCy runs locally, no API calls for anonymization

## 📊 Export Options

- **JSON**: Complete data with both coder results
- **Excel**: Formatted spreadsheet with Topics, Themes, Summary

## 🔧 Configuration

### Environment Variables (Optional for local development)

Create a `.env` file:

```bash
# OpenRouter API (can also enter in UI)
OPENROUTER_API_KEY=your_key_here
```

### Streamlit Configuration

Configured in `.streamlit/config.toml`:
- 50MB max file upload
- Custom theme
- Privacy settings

## 📄 License

QDA360 is licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).

## 🙏 Acknowledgments

QDA360 is forked from [IBM's Qux360](https://github.com/IBM/qux360), with significant modifications for:
- Dual-coder LLM architecture
- Streamlit web interface
- OpenRouter API integration

---

Built with ❤️ for qualitative researchers who value transparency and rigor.