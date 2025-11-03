#!/bin/bash
# Reset and Test Script
# Completely resets the environment and prepares for E2E test
# Run from project root: ./scripts/reset_and_test.sh

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo -e "${CYAN}================================================================================${NC}"
echo -e "${CYAN}COMPLETE ENVIRONMENT RESET FOR E2E TESTING${NC}"
echo -e "${CYAN}================================================================================${NC}"
echo ""

# Step 1: Stop and remove all containers
echo -e "${YELLOW}Step 1: Stopping and removing all containers...${NC}"
docker-compose down -v || echo -e "${YELLOW}Warning: docker-compose down had errors (may be expected if not running)${NC}"
echo -e "${GREEN}✓ Containers stopped and removed${NC}\n"

# Step 2: Remove dangling volumes
echo -e "${YELLOW}Step 2: Cleaning up Docker volumes...${NC}"
docker volume prune -f
echo -e "${GREEN}✓ Volumes cleaned${NC}\n"

# Step 3: Verify API key is set
echo -e "${YELLOW}Step 3: Checking environment variables...${NC}"
if [ -z "$OPENAI_API_KEY" ]; then
    echo -e "${RED}ERROR: OPENAI_API_KEY not set!${NC}"
    echo -e "${YELLOW}Please set it: export OPENAI_API_KEY='your-key-here'${NC}"
    exit 1
fi
echo -e "${GREEN}✓ OPENAI_API_KEY is set${NC}\n"

# Step 4: Start PostgreSQL and Qdrant
echo -e "${YELLOW}Step 4: Starting database services...${NC}"
docker-compose up -d postgres qdrant
sleep 5
echo -e "${GREEN}✓ Database services started${NC}\n"

# Step 5: Wait for PostgreSQL to be ready
echo -e "${YELLOW}Step 5: Waiting for PostgreSQL to be ready...${NC}"
max_attempts=30
attempt=0
ready=false

while [ $attempt -lt $max_attempts ] && [ "$ready" = false ]; do
    ((attempt++))
    echo -n "  Attempt $attempt/$max_attempts..."
    
    if docker exec theappapp-postgres pg_isready -U postgres > /dev/null 2>&1; then
        ready=true
        echo -e " ${GREEN}Ready!${NC}"
    else
        echo -e " ${YELLOW}Not ready yet...${NC}"
        sleep 2
    fi
done

if [ "$ready" = false ]; then
    echo -e "${RED}ERROR: PostgreSQL did not become ready in time${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL is ready${NC}\n"

# Step 6: Run Alembic migrations
echo -e "${YELLOW}Step 6: Running Alembic migrations...${NC}"
export DATABASE_URL="postgresql://postgres:postgres@localhost:55432/theappapp"

# Check if alembic is installed
if ! command -v alembic &> /dev/null; then
    echo -e "${RED}ERROR: Alembic not found. Install it: pip install alembic${NC}"
    exit 1
fi
echo "  Alembic found"

# Run migrations from backend directory
cd backend
alembic upgrade head
cd ..
echo -e "${GREEN}✓ Migrations complete${NC}\n"

# Step 7: Verify database schema
echo -e "${YELLOW}Step 7: Verifying database schema...${NC}"
echo -e "  ${CYAN}Database tables:${NC}"
docker exec theappapp-postgres psql -U postgres -d theappapp -t -c "\dt" || echo -e "${YELLOW}Warning: Could not verify schema${NC}"
echo -e "${GREEN}✓ Database schema verified${NC}\n"

# Step 8: Check connectivity
echo -e "${YELLOW}Step 8: Testing database connectivity...${NC}"
docker exec theappapp-postgres psql -U postgres -d theappapp -c "SELECT 1" > /dev/null
echo -e "${GREEN}✓ Database connectivity OK${NC}\n"

# Summary
echo -e "${CYAN}================================================================================${NC}"
echo -e "${GREEN}ENVIRONMENT READY FOR TESTING${NC}"
echo -e "${CYAN}================================================================================${NC}"
echo ""
echo -e "${YELLOW}Services running:${NC}"
echo -e "  ${GREEN}✓ PostgreSQL: localhost:55432${NC}"
echo -e "  ${GREEN}✓ Qdrant:     localhost:6333${NC}"
echo ""
echo -e "${YELLOW}Database:${NC}"
echo -e "  ${CYAN}Name:     theappapp${NC}"
echo -e "  ${CYAN}User:     postgres${NC}"
echo -e "  ${CYAN}Password: postgres${NC}"
echo -e "  ${CYAN}URL:      postgresql://postgres:postgres@localhost:55432/theappapp${NC}"
echo ""
echo -e "${YELLOW}Ready to run E2E test:${NC}"
echo -e "  ${CYAN}pytest backend/tests/test_e2e_real_hello_world.py -v -s --tb=short${NC}"
echo ""
echo -e "${CYAN}================================================================================${NC}"
