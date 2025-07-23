# Academic Paper Reference Checker

*Vibe coded by Mark Russinovich and Github Copilot Agent with Sonnet 4*

A comprehensive tool for validating reference accuracy in academic papers useful both for authors checking their bibliography and for conference reviewers checking to ensure that a paper's references are authentic and accurate. This tool can papers from various local and online sources including ArXiv, PDF files, LaTeX documents, and text files to verify the accuracy of references by comparing cited information against authoritative sources.

## 🎯 Features

- **📄 Multiple Input Formats**: Process ArXiv papers, local PDFs, LaTeX files, and text documents
- **🔍 Advanced Bibliography Detection**: Uses intelligent pattern matching to identify bibliography sections
- **🤖 LLM-Enhanced Reference Extraction**: Optional AI-powered bibliography parsing with support for OpenAI, Anthropic, Google, Azure, and local vLLM
- **✅ Comprehensive Error Detection**: Identifies issues with titles, authors, years, venus, URLs, and DOIs
- **🔄 Multi-Tier Verification Sources**: Uses a prioritized check of Semantic Scholar, OpenAlex, and CrossRef 
- **📊 Detailed Reporting**: Generates comprehensive error reports with drop-in corrected references
## Quick Start

### Check Your First Paper

1. **Check a famous paper:**
   ```bash
   python refchecker.py --paper 1706.03762
   ```

2. **Check your own PDF:**
   ```bash
   python refchecker.py --paper /path/to/your/paper.pdf
   ```

3. **For faster processing with local database** (see [Local Database Setup](#local-database-setup)):
   ```bash
   python refchecker.py --paper 1706.03762 --db-path semantic_scholar_db/semantic_scholar.db
   ```

## 🤖 LLM-Enhanced Reference Extraction

RefChecker supports AI-powered bibliography parsing using Large Language Models (LLMs) for improved accuracy with complex citation formats. While models as small as Llama 3.2-8B are fairly reliable at reference extraction, Claude Sonnet 4 has shown the best performance on large, complex bibliographies.  

### Supported LLM Providers

- **OpenAI** e.g., GPT-4o, o3
- **Anthropic** e.g., Claude Sonnet 4
- **Google** e.g., Gemini 2.5
- **Azure OpenAI** e.g., GPT-4o, o3
- **vLLM** e.g., Local Hugging Face models via OpenAI-compatible server

### Quick LLM Setup 

1. **Using Environment Variables**:
   ```bash
   # Enable LLM with Anthropic Claude
   export REFCHECKER_USE_LLM=true
   export REFCHECKER_LLM_PROVIDER=anthropic
   export ANTHROPIC_API_KEY=your_api_key_here
   
   python refchecker.py --paper 1706.03762
   ```

2. **Using Command Line Arguments**:
   ```bash
   # Enable LLM with specific provider and model
   python refchecker.py --paper 1706.03762 \
     --llm-provider anthropic \
     --llm-model claude-sonnet-4-20250514 \
   ```
   The command line supports an --llm-key parameter, but recommended usage is to set the environment variable API key setting for the provider you select. 

### LLM Configuration Options

#### Environment Variables
```bash
# Enable/disable LLM
export REFCHECKER_USE_LLM=true

# Provider selection
export REFCHECKER_LLM_PROVIDER=anthropic        # openai, anthropic, google, azure

# Provider-specific API keys (native environment variables preferred)
export OPENAI_API_KEY=your_key                    # or REFCHECKER_OPENAI_API_KEY
export ANTHROPIC_API_KEY=your_key                 # or REFCHECKER_ANTHROPIC_API_KEY
export GOOGLE_API_KEY=your_key                    # or REFCHECKER_GOOGLE_API_KEY
export AZURE_OPENAI_API_KEY=your_key              # or REFCHECKER_AZURE_API_KEY
export AZURE_OPENAI_ENDPOINT=your_endpoint        # or REFCHECKER_AZURE_ENDPOINT

# Model configuration
export REFCHECKER_LLM_MODEL=claude-sonnet-4-20250514
export REFCHECKER_LLM_MAX_TOKENS=4000
export REFCHECKER_LLM_TEMPERATURE=0.1
```

#### Command Line Arguments
```bash
# LLM provider and configuration
--llm-provider {openai,anthropic,google,azure}  # Enable LLM with specified provider
--llm-model MODEL_NAME                          # Override default model
--llm-key API_KEY                               # API key (optional if env var set)
--llm-endpoint ENDPOINT_URL                     # Override default endpoint
```

### LLM Examples

#### OpenAI GPT-4
```bash
python refchecker.py --paper /path/to/paper.pdf \
  --llm-provider openai \
  --llm-model gpt-4o \
  --llm-key sk-your-openai-key
```

#### Anthropic Claude
```bash
python refchecker.py --paper https://arxiv.org/abs/1706.03762 \
  --llm-provider anthropic \
  --llm-model claude-sonnet-4-20250514 \
  --llm-key your-anthropic-key
```

#### Google Gemini
```bash
python refchecker.py --paper paper.tex \
  --llm-provider google \
  --llm-model gemini-2.5-flash \
  --llm-key your-google-key
```

#### Azure OpenAI
```bash
python refchecker.py --paper paper.txt \
  --llm-provider azure \
  --llm-model gpt-4 \
  --llm-key your-azure-key \
  --llm-endpoint https://your-resource.openai.azure.com/
```

#### vLLM (Local Models)
```bash
# Start vLLM server first (automatic startup supported)
python refchecker.py --paper paper.pdf \
  --llm-provider vllm \
  --llm-model meta-llama/Llama-3.2-8B-Instruct 
```

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/markrussinovich/refchecker.git
cd refchecker
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. (Optional) Install Additional Dependencies

For enhanced performance and LLM support, you can install optional dependencies:

```bash
# For LLM providers
pip install openai           # For OpenAI GPT models
pip install anthropic        # For Anthropic Claude models
pip install google-generativeai  # For Google Gemini models

# For faster XML/HTML parsing
pip install lxml

# For dynamic web scraping (if needed)
pip install selenium

# For better PDF processing
pip install pikepdf
```

## 📖 Usage

Check papers in various formats and online locations:

#### ArXiv Papers

```bash
# Check a specific ArXiv paper by ID
python refchecker.py --paper 1706.03762

# Check by ArXiv URL
python refchecker.py --paper https://arxiv.org/abs/1706.03762

# Check by ArXiv PDF URL
python refchecker.py --paper https://arxiv.org/pdf/1706.03762.pdf
```

#### Local PDF Files

```bash
# Check a local PDF file
python refchecker.py --paper /path/to/your/paper.pdf

# Check with offline database for faster processing
python refchecker.py --paper /path/to/your/paper.pdf --db-path semantic_scholar_db/semantic_scholar.db
```

#### LaTeX Files

```bash
# Check a LaTeX document
python refchecker.py --paper /path/to/your/paper.tex

# Check with debug mode for detailed processing info
python refchecker.py --paper /path/to/your/paper.tex --debug
```

#### Text Files

```bash
# Check a plain text file containing paper content
python refchecker.py --paper /path/to/your/paper.txt

# Combine with local database for offline verification
python refchecker.py --paper /path/to/your/paper.txt --db-path semantic_scholar_db/semantic_scholar.db
```

## 📊 Output and Results

### Generated Files

- **`reference_errors.txt`**: Detailed error report with full context

### Error Types

- **❌ Errors**: Critical issues that need correction
  - `author`: Author name mismatches
  - `title`: Title discrepancies
  - `url`: Incorrect URLs or arXiv IDs
  - `doi`: DOI mismatches

- **⚠️ Warnings**: Minor issues that may need attention
  - `year`: Publication year differences
  - `unverified`: References that couldn't be verified

### Sample Output

```
📄 Processing: Attention Is All You Need
   URL: https://arxiv.org/abs/1706.03762

[1/45] Neural machine translation in linear time
       Nal Kalchbrenner, Lasse Espeholt, Karen Simonyan, Aaron van den Oord, Alex Graves, Koray Kavukcuoglu
       2017
         ⚠️  year: Year mismatch: cited as 2017 but actually 2016

[2/45] Effective approaches to attention-based neural machine translation
       Minh-Thang Luong, Hieu Pham, Christopher D. Manning
       2015
         ❌  author: First author mismatch: 'Minh-Thang Luong' vs 'Thang Luong'

============================================================
📋 SUMMARY
============================================================
📚 Total references processed: 68
❌ Total errors: 55
⚠️  Total warnings: 16
❓ References that couldn't be verified: 15

💾 Detailed results saved to: reference_errors.txt
```

## 🧪 Testing and Validation

### Run Validation Tests

```bash
# Test with comprehensive reference validation suite
python tests/validate_refchecker.py --db-path semantic_scholar_db/semantic_scholar.db

# Test without database (uses enhanced hybrid mode)
python tests/validate_refchecker.py

# Test specific papers
python tests/validate_papers.py --paper attention --db-path semantic_scholar_db/semantic_scholar.db
python tests/validate_papers.py --paper custom --arxiv-id 1706.03762

# Test local database functionality
python tests/validate_local_db.py --db-path semantic_scholar_db/semantic_scholar.db

# Test with debug mode for detailed output
python tests/validate_refchecker.py --debug
```

### Validation Scripts

- **`tests/validate_refchecker.py`**: Comprehensive validation suite with known good/bad references
- **`tests/validate_papers.py`**: Tests with specific papers (attention, website references, custom papers)  
- **`tests/validate_local_db.py`**: Local database functionality and integrity checks
- **`tests/validate_attention_paper.py`**: Specific validation of "Attention Is All You Need" paper

All validation scripts support:
- Local database testing (`--db-path`)
- Enhanced hybrid mode testing (default)
- Debug output (`--debug`)
- API key configuration

## ⚙️ Configuration


### Command Line Arguments

```bash
# Basic options
--paper PAPER                    # Paper to check (ArXiv ID, URL, or file path)
--debug                          # Enable debug mode
--semantic-scholar-api-key KEY   # Semantic Scholar API key
--db-path PATH                   # Local database path

# LLM options
--llm-provider {openai,anthropic,google,azure,vllm}  # Enable LLM with provider
--llm-model MODEL                # Override default model
--llm-key KEY                    # API key for LLM provider
--llm-endpoint URL               # Override endpoint (for Azure/vLLM)


## 🗄️ Local Database Setup

### Downloading the Database

Create a local database for offline verification:

```bash
# Download recent computer science papers
python download_semantic_scholar_db.py \
  --field "computer science" \
  --start-year 2020 \
  --end-year 2024 \
  --batch-size 100

# Download papers matching a specific query
python download_semantic_scholar_db.py \
  --query "attention is all you need" \
  --batch-size 50

# Download with API key for higher rate limits
python download_semantic_scholar_db.py \
  --api-key YOUR_API_KEY \
  --field "machine learning" \
  --start-year 2023
```

### Database Options

- **`--output-dir`**: Directory to store database (default: `semantic_scholar_db`)
- **`--batch-size`**: Papers per batch (default: 100)
- **`--api-key`**: Semantic Scholar API key for higher limits
- **`--fields`**: Metadata fields to include
- **`--query`**: Search query for specific papers
- **`--start-year`/`--end-year`**: Year range filter

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
