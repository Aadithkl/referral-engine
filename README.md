# Referral Engine

A sophisticated referral rewards system that uses AI-powered agents to design personalized reward curves based on user behavior and social influence.

## Overview

Referral Engine analyzes user profiles to create dynamic reward curves that adapt to individual user characteristics, moving beyond flat referral rewards to psychologically-optimized incentive structures that boost engagement and referral rates.

Built with CrewAI, FastAPI, and modern web technologies, the system features:
- 4-agent AI pipeline for user analysis and curve design
- Personalized reward curves based on user archetypes
- Real-time dashboard for curve visualization and testing
- User progress tracking and referral history
- Landing page with interactive animations and explanations
- User search functionality for administrative oversight

## Features

### AI-Powered Analysis Pipeline
- **Signal Parser**: Normalizes raw user data into structured profiles
- **Score Calculator**: Computes Reach, Advocacy, and PCU scores using LLMs with deterministic fallback
- **Ask Orchestrator**: Evaluates referral readiness and computes penalty factors
- **Curve Designer**: Creates personalized 4-phase reward curves (Hook-Valley-Surge-Plateau)

### Dynamic Reward Curves
- Four psychological phases designed to motivate user behavior
- Curves adapt to user archetype (Influencer, Broadcaster, Fan, Newcomer)
- Penalty-based adjustments for low-metric users
- Real-time preview and testing capabilities

### User Interface
- **Landing Page**: Interactive explanation with scroll-triggered video playback
- **Dashboard**: Curve designer with real-time preview and adjustment tools
- **Overview**: System-wide statistics and recent activity
- **User View**: Individual progress tracking and reward visualization
- **User Search**: Administrative interface to find and view user profiles

### Technical Architecture
- FastAPI backend with async endpoints
- SQLite persistence (PostgreSQL-ready)
- CrewAI Flow orchestration
- Modular agent design with tool integration
- RESTful API for external integrations
- Environment-based configuration

## System Requirements

- Python 3.10+
- UV package manager (recommended) or pip
- Git (for version control)
- Approximately 100MB disk space

## Installation

### Option 1: Using UV (Recommended)

```bash
# Install UV if not present
pip install uv

# Clone repository
git clone https://github.com/yourusername/referral-engine.git
cd referral-engine

# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Option 2: Using pip

```bash
git clone https://github.com/yourusername/referral-engine.git
cd referral-engine
pip install -r pyproject.toml  # or install individual dependencies
```

### Environment Setup

Create a `.env` file in the root directory:

```env
# API Keys (if using LLM features)
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEV=1  # Set to 0 in production to disable auto-reload

# Landing Page Configuration
LANDING_PAGE_DIR=/path/to/landing/page  # Optional, defaults to C:\Users\Aadith\referral-engine on Windows
```

## Usage

### Development Mode

```bash
# Start the server with auto-reload
python start.py
```

The server will automatically detect an available port (default starting at 8000) and display the URL.

### Production Mode

```bash
DEV=0 python start.py
```

Or using uvicorn directly:

```bash
uvicorn src.referral_engine.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Core Referral Analysis

- `POST /v1/referral/analyze` - Start analysis for a user
- `GET /v1/referral/results/{job_id}` - Get analysis results
- `GET /v1/referral/curves/{user_id}` - Retrieve saved reward curve
- `GET /v1/referral/curves` - List all curves (filter by archetype)
- `DELETE /v1/referral/curves/{user_id}` - Delete a curve
- `POST /v1/referral/confirm/{user_id}` - Confirm referral completion

### Curve Design & Testing

- `GET /dashboard` - Curve designer interface
- `GET /api/curve/preview` - Preview curve with test parameters
- `GET /api/curve/config` - Get dashboard configuration
- `POST /api/curve/save` - Save curve configuration

### User Management

- `GET /users` - User search interface
- `GET /api/user/progress` - List user progress (with search/filter)
- `GET /user/{user_id}` - Individual user view
- `GET /api/user/{user_id}/status` - User status API
- `GET /api/user/{user_id}/referrals` - User referral history
- `GET /api/user/progress` - Progress listing with filters

### System & Monitoring

- `GET /overview` - System overview dashboard
- `GET /api/overview` - Overview statistics API
- `GET /health` - Health check endpoint
- `POST /v1/referral/handler` - Register reward handler

### Static Assets

- `GET /` - Landing page
- `GET /style.css` - Landing page stylesheet
- `GET /main.js` - Landing page JavaScript
- `GET /assets/{filename}` - Landing page assets (videos, etc.)

## Architecture

### AI Agent Pipeline

The system uses a 4-agent CrewAI Flow:

1. **Signal Parser** - Converts raw Twitter/product data into normalized profiles
2. **Score Calculator** - Computes Reach, Advocacy, PCU, and determines user archetype
3. **Ask Orchestrator** - Evaluates readiness to ask for referrals and applies penalties
4. **Curve Designer** - Creates personalized 4-phase reward curves based on analysis

### Data Model

- **NormalizedProfile**: Standardized user characteristics
- **ScoreOutput**: Reach, Advocacy, PCU scores and archetype
- **AskDecision**: Referral readiness recommendation
- **CurvePlan**: Personalized reward curve with milestones
- **ReferralState**: Complete state flowing through the pipeline

### Persistence Layer

SQLite database with tables for:
- User progress and rewards
- Saved reward curves
- Referral confirmation history
- System statistics

## Development

### Project Structure

```
referral-engine/
├── src/
│   └── referral_engine/          # Main application package
│       ├── agents/               # AI agent implementations
│       ├── core/                 # Core algorithms (scoring, curve building, etc.)
│       ├── models/               # Pydantic data models
│       ├── state.py              # Referral state definition
│       ├── storage.py            # Database operations
│       ├── main.py               # FastAPI application
│       └── config.py             # Configuration management
├── templates/                    # HTML templates
│   ├── dashboard.html            # Curve designer
│   ├── overview.html             # System overview
│   ├── user.html                 # Individual user view
│   └── users.html                # User search interface
├── tests/                        # Test suite
├── docs/                         # Documentation
├── data/                         # Database and test data
└── start.py                      # Application entry point
```

### Running Tests

```bash
# Run test suite
python -m pytest tests/

# Run specific test categories
python -m pytest tests/test_core.py
python -m pytest tests/test_models.py
```

### Code Style

The project follows standard Python formatting conventions. Consider using tools like:
- `ruff` for linting
- `black` for formatting
- `mypy` for type checking

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for LLM features | *(required for AI features)* |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | Auto-detected (starting at 8000) |
| `DEV` | Enable development mode (auto-reload) | `1` |
| `LANDING_PAGE_DIR` | Path to landing page assets | `C:\Users\Aadith\referral-engine` |
| `BASE_REWARD` | Base reward amount for curve calculations | `100.0` |
| `QUADRANT_REACH_SPLIT` | Reach score threshold for quadrant | `50` |
| `QUADRANT_ADVOCACY_SPLIT` | Advocacy score threshold for quadrant | `50` |
| `OPTIMAL_ZONE_PERCENTAGE` | Percentage of PCU for optimal zone | `0.5` |
| `PENALTY_FLOOR_GLOBAL` | Minimum penalty factor | `0.05` |

### Agent Configuration

Agent behaviors can be customized through:
- `src/referral_engine/config/agents.yaml` - Agent roles and backstories
- `src/referral_engine/config/tasks.yaml` - Task definitions and workflows

## Deployment

### Docker (Optional)

Create a Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8000
ENV HOST=0.0.0.0 PORT=8000 DEV=0

CMD ["python", "start.py"]
```

Build and run:

```bash
docker build -t referral-engine .
docker run -p 8000:8000 referral-engine
```

### Environment-Specific Configuration

Create separate `.env` files for different environments:
- `.env.development` - Development settings
- `.env.staging` - Staging settings  
- `.env.production` - Production settings

Then load the appropriate file:
```bash
# Development
DEV=1 python start.py

# Production
DEV=0 python start.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Write tests for new features
- Follow existing code style
- Document new API endpoints
- Keep agents focused on single responsibilities
- Ensure deterministic fallbacks for LLM operations

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [CrewAI](https://crewai.com) for the multi-agent framework
- [FastAPI](https://fastapi.tiangolo.com) for the high-performance API framework
- [Chart.js](https://www.chartjs.org) for data visualization
- [GSAP](https://greensock.com/gsap) for animations
- [Lenis](https://github.com/studio-freight/lenis) for smooth scrolling

## Contact

Aadith Narayanan - [GitHub Profile](https://github.com/Aadithkl)

Project Link: [https://github.com/Aadithkl/referral-engine](https://github.com/Aadithkl/referral-engine)