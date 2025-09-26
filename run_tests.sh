#!/bin/bash

# Quick test runner for Chat Agent PoC
# Provides easy access to different testing scenarios

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}$1${NC}\n"
}

print_option() {
    echo -e "${GREEN}$1${NC} - $2"
}

show_menu() {
    print_header "Chat Agent PoC - Test Suite"
    echo "Choose a testing scenario:"
    echo ""
    print_option "1" "Test Experienced Business Manager (knows exact requirements)"
    print_option "2" "Test Novice User (learning workflow design)"
    print_option "3" "Run Full Conversation Test Suite"
    print_option "4" "Verify Existing Workflows"
    print_option "5" "Quick Health Check"
    print_option "6" "Manual Chat Test"
    print_option "q" "Quit"
    echo ""
}

health_check() {
    print_header "Health Check"

    echo "Checking AI Agent (port 8001)..."
    if curl -s http://localhost:8001/api/v1/health > /dev/null; then
        echo "✅ AI Agent: Running"
    else
        echo "❌ AI Agent: Not responding"
        return 1
    fi

    echo "Checking svc-builder (port 8000)..."
    if curl -s http://localhost:8000/api/v1/health > /dev/null; then
        echo "✅ svc-builder: Running"
    else
        echo "❌ svc-builder: Not responding"
        return 1
    fi

    echo ""
    echo "🎉 All services are healthy!"
}

manual_chat() {
    print_header "Manual Chat Test"
    echo "Enter your message (or 'quit' to exit):"

    while true; do
        echo -n "You: "
        read -r message

        if [[ "$message" == "quit" ]]; then
            break
        fi

        echo ""
        echo "🤖 AI Response:"
        curl -s -X POST "http://localhost:8001/api/v1/chat" \
            -H "Content-Type: application/json" \
            -d "{\"message\": \"$message\"}" | \
            python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('response', 'No response'))
except:
    print('Error: Could not parse response')
"
        echo ""
    done
}

main() {
    while true; do
        show_menu
        echo -n "Enter your choice: "
        read -r choice

        case $choice in
            1)
                echo ""
                ./test_conversations.sh manager
                ;;
            2)
                echo ""
                ./test_conversations.sh novice
                ;;
            3)
                echo ""
                ./test_conversations.sh all
                ;;
            4)
                echo ""
                ./test_conversations.sh verify
                ;;
            5)
                echo ""
                health_check
                ;;
            6)
                echo ""
                manual_chat
                ;;
            q|Q)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo "Invalid option. Please try again."
                ;;
        esac

        echo ""
        echo -e "${YELLOW}Press Enter to continue...${NC}"
        read -r
    done
}

# Check if test script exists
if [[ ! -f "./test_conversations.sh" ]]; then
    echo "Error: test_conversations.sh not found in current directory"
    echo "Please run this script from the chat-agent project root"
    exit 1
fi

main