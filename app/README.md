# Fashion Recommendations Dashboard

A FastAPI-based dashboard for analyzing fashion product recommendations, customer demographics, and sales trends deployed on Databricks Apps.

## 🌟 Features

- **Bestseller Analysis**: View top-selling products with filters for date range, category, and more
- **Customer Demographics**: Visualize customer age distribution, club membership, and fashion news subscriptions
- **Time Series Analysis**: Track sales, revenue, and customer trends over time
- **Product Explorer**: Search and filter through product catalog with pagination

## 📁 Project Structure

```
app/
├── app.py                     # Main FastAPI application
├── app.yaml                   # Databricks Apps runtime config
├── db.py                      # Database connection utilities
├── settings.py                # Application settings
├── requirements.txt           # Python dependencies
├── Makefile                   # Task automation (recommended)
├── databricks.yml            # Databricks bundle config (optional)
├── .gitignore                # Git ignore patterns
├── scripts/                   # Deployment and utility scripts
│   ├── deploy.py             # Python deployment script
│   ├── deploy.sh             # Shell deployment script
│   ├── run.sh                # Local development script
│   └── test_deployment.py    # Deployment tests
├── templates/                 # Jinja2 HTML templates
│   ├── base.html
│   ├── bestsellers.html
│   ├── demographics.html
│   ├── explorer.html
│   └── timeseries.html
└── static/                    # Static assets (CSS)
    └── styles.css
```

## 🛠️ Technology Stack

- **Framework**: FastAPI
- **Server**: Uvicorn
- **Templates**: Jinja2
- **Data Processing**: Pandas
- **Visualization**: Plotly
- **Database**: Databricks Unity Catalog (via SQL connector)
- **SDK**: Databricks SDK
- **Deployment**: Databricks Apps

---

## 🚀 Quick Start

### Using Makefile (Recommended)

```bash
# Show all available commands
make help

# First time setup and deployment
make first-deploy

# Deploy to dev (default)
make deploy

# Deploy to production
make deploy-prod

# Run locally for testing
make run
```

### Using Scripts Directly

```bash
# Run locally for testing
./scripts/run.sh

# Deploy to dev environment (default)
./scripts/deploy.sh

# Deploy to production
./scripts/deploy.sh prod
```

Access the local app at `http://localhost:8000`

---

## 📋 Prerequisites

### 1. Databricks CLI

Install the Databricks CLI (version >= 0.239.0):

```bash
pip install databricks-cli
```

Verify installation:

```bash
databricks --version
```

### 2. Authentication

#### For Local Development

Set environment variables with your Databricks credentials:

```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-personal-access-token"
```

To get a personal access token:
1. Go to your Databricks workspace
2. Click on your profile → Settings
3. Navigate to Developer → Access tokens
4. Click "Generate new token"

Alternatively, create a `.env` file in the `app/` directory:

```bash
# Copy the example file and fill in your credentials
cp env.example .env
# Edit .env with your actual values
```

Example `.env` file:
```bash
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=dapi1234567890abcdef
CATALOG_NAME=jongseob_demo
SCHEMA_NAME=fashion_recommendations
```

> **Note**: The `.env` file is gitignored for security. Never commit tokens to version control.

#### For Deployment

Authenticate with the Databricks CLI for deployment operations:

```bash
databricks auth login --host https://e2-demo-field-eng.cloud.databricks.com/
```

Verify authentication:

```bash
databricks auth profiles  # Should show YES for a valid profile
```

> **Note**: On Databricks Apps, authentication is handled automatically through the app's service principal. No additional configuration is needed.

### 3. Python Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

---

## 🔧 Configuration

### Environment Variables

Configure in `app.yaml`:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (dev/prod) | `dev` |
| `CATALOG_NAME` | Unity Catalog name | `jongseob_demo` |
| `SCHEMA_NAME` | Schema name | `fashion_recommendations` |
| `VOLUME_PATH` | Volume path for images | `/Volumes/jongseob_demo/fashion_recommendations/data` |

### app.yaml Structure

```yaml
command:
  - uvicorn
  - app:app
  - --host
  - "0.0.0.0"
  - --port
  - "8080"

env:
  - name: APP_ENV
    value: "dev"  # or "prod"
  - name: CATALOG_NAME
    value: "jongseob_demo"
  - name: SCHEMA_NAME
    value: "fashion_recommendations"
  - name: VOLUME_PATH
    value: "/Volumes/jongseob_demo/fashion_recommendations/data"
```

### API Scopes

The app requires these Databricks API scopes:
- `sql` - Execute SQL queries
- `files.files` - Access files in volumes
- `catalog.catalogs:read` - Read catalog metadata
- `catalog.schemas:read` - Read schema metadata
- `catalog.tables:read` - Read table data

---

## 📊 Data Requirements

The app expects the following tables in Unity Catalog:

- `articles_synced` - Product catalog
- `product_sales_summary_synced` - Sales summary by product
- `customer_demographics_synced` - Customer demographics
- `time_series_sales_synced` - Time series sales data

And product images in:
- `/Volumes/{catalog}/{schema}/data/images/` - Product images organized by folders

---

## 🚢 Deployment

### Method 1: Using Makefile (Recommended)

The Makefile provides convenient shortcuts for all common tasks:

```bash
# First time deployment (install + auth + deploy)
make first-deploy

# Deploy to dev
make deploy

# Deploy to production
make deploy-prod

# Quick deploy (sync + deploy)
make quick-deploy

# Full deployment with validation
make full-deploy-dev
```

### Method 2: Using Scripts

Use the deployment scripts for automated deployment:

```bash
# Deploy to dev
./scripts/deploy.sh

# Deploy to production
./scripts/deploy.sh prod
```

**What it does:**
1. Validates configuration files (app.yaml, requirements.txt, app.py)
2. Checks Databricks authentication
3. Syncs source code to Databricks workspace
4. Creates app if it doesn't exist
5. Starts app compute
6. Deploys the application code

**Expected Output:**
```
==========================================
Deploying Fashion Recommendations App
Target: dev
App Name: fashion-rec-app-dev
==========================================

✓ Authentication verified
✓ All required files present
✓ Connected to workspace
✓ Source code synced successfully
✓ App compute is active
✓ App deployed successfully

==========================================
✅ Deployment Successful!
==========================================

🌐 App URL: https://fashion-rec-app-dev-1444828305810485.aws.databricksapps.com
```

### Method 2: Manual Deployment

For more control over the deployment process:

#### Step 1: Sync Source Code

```bash
# One-time sync
databricks sync . /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev

# Or continuous sync with watch mode
databricks sync --watch . /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev
```

#### Step 2: Start App

```bash
databricks apps start fashion-rec-app-dev
```

#### Step 3: Deploy Code

```bash
databricks apps deploy fashion-rec-app-dev \
  --source-code-path /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev
```

### Method 3: Manual Deployment with Databricks CLI

Direct CLI commands for full control:

```bash
# Sync code
databricks sync . /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev

# Deploy
databricks apps deploy fashion-rec-app-dev \
  --source-code-path /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev
```

### Method 4: Using Python Script Directly

```bash
# Deploy to dev
python3 scripts/deploy.py

# Deploy to prod
python3 scripts/deploy.py prod
```

---

## 🌍 Environments

### Development (dev)

- **App Name**: `fashion-rec-app-dev`
- **Workspace Path**: `/Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev`
- **Environment**: Development mode with debug logging
- **Target**: Testing and development

```bash
./scripts/deploy.sh dev
```

### Production (prod)

- **App Name**: `fashion-rec-app-prod`
- **Workspace Path**: `/Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-prod`
- **Environment**: Production mode
- **Target**: Live production workloads

```bash
./scripts/deploy.sh prod
```

**Important**: Update `app.yaml` environment variables for production settings before deploying.

---

## 🔍 Monitoring & Management

### Using Makefile

```bash
# Check dev app status
make status

# Check prod app status
make status-prod

# View dev app logs
make logs

# View prod app logs
make logs-prod

# List all apps
make list

# Show app info and URLs
make info
```

### Using Databricks CLI Directly

```bash
# List all apps
databricks apps list

# Get specific app details
databricks apps get fashion-rec-app-dev

# Filter for fashion apps
databricks apps list | grep fashion

# View app details with JSON output
databricks apps get fashion-rec-app-dev --output json
```

### View App Logs

Access logs through:
1. Databricks UI → Apps → fashion-rec-app-dev → Logs
2. CLI: `databricks apps logs fashion-rec-app-dev`

### Stop/Start App

**Using Makefile:**
```bash
# Stop dev app
make stop

# Start dev app
make start

# Restart dev app
make restart

# Stop/start/restart prod app
make stop-prod
make start-prod
make restart-prod
```

**Using CLI:**
```bash
# Stop the app
databricks apps stop fashion-rec-app-dev

# Start the app
databricks apps start fashion-rec-app-dev
```

### Update Deployed Code

After making changes to your code:

```bash
# Option 1: Use Makefile (recommended)
make redeploy              # Redeploy to dev
make redeploy-prod         # Redeploy to prod

# Option 2: Use deployment script
./scripts/deploy.sh

# Option 3: Manual sync and deploy
databricks sync . /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev
databricks apps deploy fashion-rec-app-dev \
  --source-code-path /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev
```

### Delete App

```bash
databricks apps delete fashion-rec-app-dev
```

---

## 🎯 Application Endpoints

- `/` - Bestseller products analysis
- `/demographics` - Customer demographics visualization
- `/timeseries` - Time series sales analysis
- `/explorer` - Product catalog explorer
- `/api/image?article_id={id}` - Product image API

---

## 🐛 Troubleshooting

### Authentication Errors

**Error**: `tls: failed to verify certificate`

**Solution**: 
```bash
databricks auth login --host https://e2-demo-field-eng.cloud.databricks.com/
```

### App Creation Failed

**Error**: `App already exists`

**Solution**: The app exists but may be in a bad state. Check status and consider deleting:
```bash
databricks apps get fashion-rec-app-dev
databricks apps delete fashion-rec-app-dev
./scripts/deploy.sh
```

### Deployment In Progress

**Error**: `Cannot deploy app as there is an active deployment in progress`

**Solution**: Wait for the current deployment to complete (usually 1-2 minutes) or check app status:
```bash
databricks apps get fashion-rec-app-dev
```

### Sync Failed

**Error**: Sync command fails or times out

**Solutions**:
1. Check authentication: `databricks auth profiles`
2. Verify workspace path is accessible
3. Check network connectivity
4. Try syncing a single file first to test: `databricks sync app.py /Workspace/Users/.../test.py`

### App Not Starting

**Error**: App compute stays in `STARTING` state

**Solutions**:
1. Check app logs in Databricks UI
2. Verify `app.yaml` configuration is correct
3. Check that dependencies in `requirements.txt` are valid
4. Ensure resource limits aren't exceeded in your workspace

### Missing Dependencies

**Error**: Import errors or module not found in app logs

**Solution**: Ensure all dependencies are listed in `requirements.txt` and redeploy:
```bash
./scripts/deploy.sh
```

### Database Connection Issues

**Error**: Cannot connect to Unity Catalog tables

**Solutions**:
1. Verify the app has correct API scopes (sql, catalog access)
2. Check that catalog, schema, and tables exist
3. Verify service principal permissions
4. Check environment variables in `app.yaml`

### Deployment Stuck

```bash
# Check app status
databricks apps get fashion-rec-app-dev

# Stop and restart
databricks apps stop fashion-rec-app-dev
sleep 5
databricks apps start fashion-rec-app-dev
sleep 10
./scripts/deploy.sh
```

---

## 📋 Makefile Commands

The project includes a comprehensive Makefile for easy task management. Run `make help` to see all available commands:

### Most Common Commands

```bash
make help              # Show all available commands
make first-deploy      # First time setup (install + auth + deploy)
make deploy            # Deploy to dev
make deploy-prod       # Deploy to production
make run               # Run locally
make status            # Check dev app status
make logs              # View dev app logs
make info              # Show app URLs and configuration
```

### Quick Reference by Category

**Development:**
- `make install` - Install dependencies
- `make run` - Run locally
- `make test` - Run tests
- `make clean` - Clean temporary files

**Deployment:**
- `make deploy` - Deploy to dev
- `make deploy-prod` - Deploy to production
- `make quick-deploy` - Sync + deploy to dev
- `make redeploy` - Redeploy dev after changes
- `make promote` - Promote dev to production

**Management:**
- `make status` / `make status-prod` - Check app status
- `make logs` / `make logs-prod` - View logs
- `make start` / `make stop` - Start/stop dev app
- `make restart` - Restart dev app
- `make list` - List all apps

**Sync:**
- `make sync` - One-time sync to dev
- `make sync-watch` - Continuous sync (watch mode)
- `make sync-prod` - One-time sync to prod

**Auth & Info:**
- `make auth` - Authenticate with Databricks
- `make auth-status` - Check auth status
- `make info` - Show app URLs
- `make version` - Show CLI versions

---

## ⚡ Common Workflows

### First Time Deployment

**Using Makefile (recommended):**
```bash
make first-deploy
```

**Using scripts:**
```bash
# 1. Authenticate
databricks auth login --host https://e2-demo-field-eng.cloud.databricks.com/

# 2. Deploy
./scripts/deploy.sh
```

### Update After Code Changes

**Using Makefile:**
```bash
make redeploy          # Redeploy to dev
make redeploy-prod     # Redeploy to prod
```

**Using scripts:**
```bash
# Just run deploy again (it syncs + deploys)
./scripts/deploy.sh
```

### Deploy to Both Environments

**Using Makefile:**
```bash
# Deploy to dev
make deploy

# Test in dev, then promote to prod
make promote
```

**Using scripts:**
```bash
# Deploy to dev
./scripts/deploy.sh dev

# Test in dev, then deploy to prod
./scripts/deploy.sh prod
```

### Continuous Development with Auto-Sync

```bash
# Terminal 1: Keep sync running with watch mode
databricks sync --watch . /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev

# Terminal 2: After making changes, redeploy
databricks apps deploy fashion-rec-app-dev \
  --source-code-path /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev
```

### Rollback to Previous Version

```bash
# Stop current app
databricks apps stop fashion-rec-app-dev

# Sync old code version
git checkout <previous-commit>
databricks sync . /Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-dev

# Redeploy
./scripts/deploy.sh
```

---

## 🔐 Security Considerations

### API Scopes

The app is configured with the following user API scopes:
- `sql` - Execute SQL queries
- `files.files` - Access files in volumes
- `catalog.catalogs:read` - Read catalog metadata
- `catalog.schemas:read` - Read schema metadata
- `catalog.tables:read` - Read table metadata

These scopes determine what data the app can access on behalf of users.

### Service Principal

Each app gets its own service principal with the configured permissions. The service principal ID can be found in the app details.

### Environment Variables

Sensitive data (credentials, tokens) should NOT be hardcoded in `app.yaml`. Use:
- Databricks secrets: `valueFrom: secrets/<scope>/<key>`
- Workspace environment variables
- Unity Catalog credentials

---

## 🚀 Performance Optimization

### App Compute

Apps use shared compute resources. For better performance:
- Minimize startup time by keeping dependencies lean
- Use connection pooling for database connections
- Cache frequently accessed data
- Optimize SQL queries

### Code Optimization

- Use async/await for I/O operations in FastAPI
- Implement proper error handling to avoid crashes
- Use pagination for large data sets
- Optimize image loading from volumes

---

## 👥 Contributing

1. Make changes locally
2. Test with `./scripts/run.sh`
3. Deploy to dev: `./scripts/deploy.sh`
4. Test in dev environment
5. Deploy to prod: `./scripts/deploy.sh prod`

---

## 📚 Additional Resources

- [Databricks Apps Documentation](https://docs.databricks.com/en/dev-tools/apps/)
- [Databricks CLI Documentation](https://docs.databricks.com/en/dev-tools/cli/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)

---

## 🎯 Success Indicators

After deployment, you should see:

```
==========================================
✅ Deployment Successful!
==========================================

🌐 App URL: https://fashion-rec-app-dev-...
📊 Monitor your app:
   databricks apps get fashion-rec-app-dev
```

App status should show:
- **Compute Status**: `ACTIVE`
- **Deployment Status**: `SUCCEEDED`
- **App Status**: `RUNNING`

---

## 🆘 Support

For issues or questions:
1. Check app logs in Databricks UI
2. Review this documentation
3. Verify Databricks CLI version: `databricks --version`
4. Check authentication: `databricks auth profiles`
5. Contact the development team

---

## 📝 License

Internal project for Databricks Field Engineering.

## 🎉 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Databricks Apps](https://docs.databricks.com/en/dev-tools/apps/)
- [Plotly](https://plotly.com/)
- [Pandas](https://pandas.pydata.org/)
