#!/usr/bin/env bash
# ------------------------------------------------------------------
# VentureStrat — Stripe Webhook Configuration
#
# This script documents and configures the Stripe webhook endpoints
# required for the billing-service subscription lifecycle.
#
# Usage:
#   ./scripts/configure_stripe.sh              # Show configuration steps
#   ./scripts/configure_stripe.sh --dev        # Start local Stripe listener
#   ./scripts/configure_stripe.sh --create     # Create production webhook via Stripe CLI
# ------------------------------------------------------------------

set -euo pipefail

BILLING_PORT="${BILLING_PORT:-8063}"
DOMAIN="${DOMAIN:-}"

# Stripe events the billing-service subscribes to
EVENTS=(
  "checkout.session.completed"
  "customer.subscription.updated"
  "customer.subscription.deleted"
  "invoice.payment_succeeded"
  "invoice.payment_failed"
)

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
  echo ""
  echo -e "${BOLD}${CYAN}VentureStrat — Stripe Webhook Configuration${NC}"
  echo -e "${CYAN}=============================================${NC}"
  echo ""
}

print_events() {
  echo -e "${BOLD}Subscribed Events:${NC}"
  for evt in "${EVENTS[@]}"; do
    echo "  - $evt"
  done
  echo ""
}

print_dev_instructions() {
  echo -e "${BOLD}${GREEN}Development Setup${NC}"
  echo "  Webhook URL: http://localhost:${BILLING_PORT}/api/v1/stripe/webhook"
  echo ""
  echo "  Prerequisites:"
  echo "    1. Install Stripe CLI: brew install stripe/stripe-cli/stripe"
  echo "    2. Authenticate: stripe login"
  echo ""
  echo "  Start local listener:"
  echo "    stripe listen \\"
  echo "      --forward-to localhost:${BILLING_PORT}/api/v1/stripe/webhook \\"
  echo "      --events $(IFS=,; echo "${EVENTS[*]}")"
  echo ""
  echo "  The CLI will print a webhook signing secret (whsec_...). Set it in your .env:"
  echo "    STRIPE_WEBHOOK_SECRET=whsec_..."
  echo ""
}

print_prod_instructions() {
  local domain="${DOMAIN:-your-domain.com}"
  echo -e "${BOLD}${GREEN}Production Setup${NC}"
  echo "  Webhook URL: https://${domain}/api/v1/stripe/webhook"
  echo ""
  echo "  Steps:"
  echo "    1. Go to https://dashboard.stripe.com/webhooks"
  echo "    2. Click 'Add endpoint'"
  echo "    3. Enter URL: https://${domain}/api/v1/stripe/webhook"
  echo "    4. Select events:"
  for evt in "${EVENTS[@]}"; do
    echo "       - $evt"
  done
  echo "    5. Click 'Add endpoint'"
  echo "    6. Copy the signing secret (whsec_...)"
  echo "    7. Set environment variable: STRIPE_WEBHOOK_SECRET=whsec_..."
  echo ""
  echo "  Or use Stripe CLI:"
  echo "    stripe webhook_endpoints create \\"
  echo "      --url https://${domain}/api/v1/stripe/webhook \\"
  echo "      --enabled-events $(IFS=,; echo "${EVENTS[*]}")"
  echo ""
}

print_env_vars() {
  echo -e "${BOLD}${YELLOW}Required Environment Variables${NC}"
  echo "  STRIPE_SECRET_KEY        — Stripe API secret key (sk_live_... or sk_test_...)"
  echo "  STRIPE_PUBLISHABLE_KEY   — Stripe publishable key (pk_live_... or pk_test_...)"
  echo "  STRIPE_WEBHOOK_SECRET    — Webhook signing secret (whsec_...)"
  echo "  STRIPE_PRICE_ID_STARTER  — Price ID for Starter plan"
  echo "  STRIPE_PRICE_ID_PRO      — Price ID for Pro plan"
  echo "  STRIPE_PRICE_ID_SCALE    — Price ID for Scale plan"
  echo ""
}

start_dev_listener() {
  echo -e "${GREEN}Starting Stripe webhook listener...${NC}"
  echo ""
  exec stripe listen \
    --forward-to "localhost:${BILLING_PORT}/api/v1/stripe/webhook" \
    --events "$(IFS=,; echo "${EVENTS[*]}")"
}

create_prod_webhook() {
  if [ -z "$DOMAIN" ]; then
    echo -e "\033[91mError: DOMAIN environment variable is required for --create\033[0m"
    echo "  Usage: DOMAIN=app.venturestrat.com ./scripts/configure_stripe.sh --create"
    exit 1
  fi
  echo -e "${GREEN}Creating production webhook endpoint...${NC}"
  stripe webhook_endpoints create \
    --url "https://${DOMAIN}/api/v1/stripe/webhook" \
    --enabled-events "$(IFS=,; echo "${EVENTS[*]}")"
}

# Main
print_header

case "${1:-}" in
  --dev)
    start_dev_listener
    ;;
  --create)
    create_prod_webhook
    ;;
  *)
    print_events
    print_dev_instructions
    print_prod_instructions
    print_env_vars
    ;;
esac
