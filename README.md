# Querionyx: Hybrid RAG + SQL System for Natural Language Database Queries

## Project Overview
Querionyx is a thesis project (2023-2025) that combines Retrieval-Augmented Generation (RAG) with SQL generation to enable natural language queries on databases like Northwind.

**Goal**: Convert user questions in natural language to executable SQL queries with semantic understanding and explainability.

## Technology Stack
- **Backend**: FastAPI + Python 3.14
- **Database**: PostgreSQL 15 (Northwind)
- **Vector Store**: ChromaDB (document retrieval)
- **LLM**: OpenAI GPT-4 via LangChain
- **Containerization**: Docker + Docker Compose
- **Version Control**: Git/GitHub

## Quick Start

### Prerequisites
- Python 3.13
- Docker & Docker Compose
- OpenAI API key

### Setup

1. **Clone repository and navigate to project**:
   ```bash
   cd c:\Data\Project\querionyx
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key
   - Configure PostgreSQL credentials (default: postgres/postgres)

5. **Start Docker containers**:
   ```bash
   docker-compose up -d
   ```

6. **Verify setup**:
   ```bash
   python test_connection.py
   # Expected output: ChromaDB OK, PostgreSQL OK
   ```

## Project Structure

```
querionyx/
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── rag/              # RAG pipeline
│   ├── router/           # Query routing logic
│   ├── sql/              # SQL generation & validation
│   └── hybrid/           # Hybrid retrieval strategy
├── data/
│   ├── raw/              # Raw datasets
│   ├── processed/        # Processed data
│   └── test_queries/     # Test query sets
├── tests/                # Unit tests
├── docs/
│   ├── data_prep/        # PDF, chunking, and schema inspection notes
│   ├── evaluation/       # Router/RAG evaluation reports and templates
│   ├── research/         # Paper notes
│   └── week3/            # Week 3 summary and validation audit
│   
├── .env                  # Environment variables (git-ignored)
├── .env.example          # Example env template
├── docker-compose.yml    # PostgreSQL + ChromaDB services
├── requirements.txt      # Python dependencies
├── test_connection.py    # Connectivity verification script
└── README.md             # This file
```

## Key Features (Planned)

### Phase 1: Foundation (Weeks 1-3)
- Environment setup
- Query router (classify intent: analytical, transactional, etc.)
- Schema retriever (identify relevant tables/columns)

### Phase 2: Generation (Weeks 3-5)
- SQL generator with LLM + few-shot examples
- SQL validation & safety checks
- Answer synthesis from query results

### Phase 3: Retrieval (Weeks 5-7)
- Document retriever (enterprise knowledge base)
- Semantic retriever (similar query lookup)
- Multi-retriever fusion strategies

### Phase 4: Evaluation (Weeks 7-10)
- Evaluation framework (RAGAS-inspired metrics)
- Performance benchmarking
- Thesis writing

## Development Tasks

### Week 1 (Completed)
- [x] Project structure & dependencies
- [x] PostgreSQL + ChromaDB containers
- [x] Environment configuration
- [x] Test connectivity verified
- [x] 5 papers reviewed & noted
- [x] Thesis outline drafted
- [x] Submission checklist ready

### Week 2 (Upcoming)
- [ ] Query router module
- [ ] Schema retriever implementation
- [ ] FastAPI app scaffold

### Weeks 3-10
Upcoming

## Documentation

### For Development
- [test_connection.py](test_connection.py) - Verify ChromaDB & PostgreSQL connectivity
- [docker-compose.yml](docker-compose.yml) - Infrastructure as code
- [requirements.txt](requirements.txt) - Python dependencies

## Architecture Overview

```
User Query (Natural Language)
    ↓
┌─────────────────────────────┐
│   Query Router              │
│ (Intent Classification)     │
└──────────┬──────────────────┘
           │
    ┌──────┴──────┐
    ↓             ↓
SQL Path       Doc Path
    │             │
    ├─→ Schema    ├─→ Document
    │   Retriever │   Retriever
    │             │
    ├─→ SQL Gen   ├─→ Answer Gen
    │             │
    └─→ Validate  └─→ Explain
           │             │
           └─────┬───────┘
                 ↓
         PostgreSQL Execution
                 ↓
         Result + Explanation
```

## Evaluation Metrics

Based on RAGAS framework + SQL-specific metrics:

1. **SQL Correctness** (0-1): Valid syntax, no errors
2. **Semantic Accuracy** (0-1): Correct result set
3. **Context Precision** (0-1): Relevant tables retrieved
4. **Faithfulness** (0-1): Explanation matches logic
5. **Answer Relevancy** (0-1): Addresses user intent
6. **Intent Alignment** (0-1): Query matches question

## Database: Northwind

- **Tables**: 10 (Categories, Customers, Employees, Orders, Products, etc.)
- **Relationships**: Complex JOINs for rich query patterns
- **Test Coverage**: Simple SELECT → Complex multi-table queries with aggregations

## Running Tests

```bash
# Verify connectivity
python test_connection.py

# (Upcoming) Run unit tests
pytest tests/

# (Upcoming) Run evaluation suite
python -m evaluation.run_benchmarks
```

## API Endpoints (Planned)

```bash
POST /query           # Natural language to SQL + result
GET  /explain/:id     # Get explanation for executed query
GET  /health          # Service health check
```

Example:
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 best-selling products?"}'
```

## Environment Variables

See `.env.example`:
```
OPENAI_API_KEY=sk-...          # OpenAI API key
PG_HOST=localhost              # PostgreSQL host
PG_PORT=5432                   # PostgreSQL port
PG_USER=user                   # PostgreSQL user
PG_PASSWORD=password           # PostgreSQL password
PG_DB=northwind                # Target database
CHROMADB_HOST=localhost        # ChromaDB host
CHROMADB_PORT=8000             # ChromaDB port
```

## Common Issues & Troubleshooting

### Docker containers won't start
```bash
# Check logs
docker-compose logs postgres
docker-compose logs chromadb

# Rebuild and restart
docker-compose down -v
docker-compose up -d
```

### test_connection.py fails on PostgreSQL
- Verify `.env` has correct credentials
- Check docker-compose is running: `docker ps`
- Ensure postgres container is healthy: `docker-compose ps`

### ChromaDB connection timeout
- Wait 30 seconds after docker-compose up (container initialization)
- Verify port 8000 is not in use: `netstat -an | findstr :8000`

## Contact & References

- **Advisor**: [...]
- **Student**: [...]
- **Project Repository**: [GitHub URL - to be added]
- **Submission Date**: 17/04/2026

## References

1. Lewis et al. (2020) - Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
2. Yu et al. (2018) - Spider: A Large-Scale Dataset for Complex and Cross-Domain Semantic Parsing
3. Gao et al. (2023) - Retrieval-Augmented Generation for Large Language Models: A Survey
4. Gao et al. (2024) - Modular RAG: Transforming RAG Systems into Adaptive, Modular Architectures
5. Es et al. (2023) - RAGAS: Automated Evaluation of Retrieval Augmented Generation

---

**Status**: Week 1 Complete
**Next Phase**: Week 2 Development  
**Last Updated**: 19/04/2026
