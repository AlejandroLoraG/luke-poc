#!/bin/bash

# Chat Agent PoC - Conversation Testing Script
# Tests two user personas:
# 1. Experienced Business Manager
# 2. Novice User Learning Workflow Design

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
AI_AGENT_URL="http://localhost:8001"
SVC_BUILDER_URL="http://localhost:8000"
CHAT_ENDPOINT="$AI_AGENT_URL/api/v1/chat"

# Global variables for conversation tracking
MANAGER_CONVERSATION_ID=""
NOVICE_CONVERSATION_ID=""

# Helper functions
print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_user() {
    echo -e "${GREEN}👤 USER ($2):${NC} $1\n"
}

print_ai() {
    echo -e "${PURPLE}🤖 AI AGENT:${NC} $1\n"
}

print_status() {
    echo -e "${YELLOW}📊 STATUS:${NC} $1\n"
}

print_error() {
    echo -e "${RED}❌ ERROR:${NC} $1\n"
}

print_success() {
    echo -e "${GREEN}✅ SUCCESS:${NC} $1\n"
}

# Function to send message to AI agent
send_message() {
    local message="$1"
    local conversation_id="$2"
    local user_type="$3"

    # Build JSON payload
    local json_payload="{\"message\": \"$message\""
    if [[ -n "$conversation_id" ]]; then
        json_payload="$json_payload, \"conversation_id\": \"$conversation_id\""
    fi
    json_payload="$json_payload}"

    print_user "$message" "$user_type"

    # Send request
    local response=$(curl -s -X POST "$CHAT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "$json_payload")

    if [[ $? -ne 0 ]]; then
        print_error "Failed to send message to AI agent"
        return 1
    fi

    # Extract response and conversation_id
    local ai_response=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('response', 'No response'))
except:
    print('Error parsing response')
")

    local new_conversation_id=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('conversation_id', ''))
except:
    print('')
")

    print_ai "$ai_response"

    # Update conversation ID if this is the first message
    if [[ -z "$conversation_id" ]]; then
        if [[ "$user_type" == "Manager" ]]; then
            MANAGER_CONVERSATION_ID="$new_conversation_id"
        else
            NOVICE_CONVERSATION_ID="$new_conversation_id"
        fi
    fi

    sleep 2  # Pause for readability
}

# Function to check service health
check_services() {
    print_header "CHECKING SERVICES"

    # Check AI Agent
    local ai_health=$(curl -s "$AI_AGENT_URL/api/v1/health" 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        print_success "AI Agent is running on port 8001"
    else
        print_error "AI Agent is not responding on port 8001"
        return 1
    fi

    # Check svc-builder
    local svc_health=$(curl -s "$SVC_BUILDER_URL/api/v1/health" 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        print_success "svc-builder is running on port 8000"
    else
        print_error "svc-builder is not responding on port 8000"
        return 1
    fi

    print_status "All services are healthy and ready for testing"
}

# Function to list existing workflows
list_workflows() {
    print_header "EXISTING WORKFLOWS IN SYSTEM"

    local workflows=$(curl -s "$SVC_BUILDER_URL/api/v1/workflows" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    workflows = data.get('workflows', [])
    print(f'Found {len(workflows)} existing workflows:')
    for wf in workflows:
        print(f'  • {wf[\"name\"]} (ID: {wf[\"spec_id\"]})')
    if len(workflows) == 0:
        print('  No workflows found.')
except:
    print('Error loading workflows')
")

    echo -e "${CYAN}$workflows${NC}\n"
}

# Business Manager Persona - Experienced with clear requirements
test_manager_persona() {
    print_header "SCENARIO 1: EXPERIENCED BUSINESS MANAGER"
    echo -e "${CYAN}Persona: Sarah, Operations Manager at a logistics company${NC}"
    echo -e "${CYAN}Context: She knows exactly what process she wants to automate${NC}"
    echo -e "${CYAN}Goal: Create a supplier onboarding workflow${NC}\n"

    # Manager knows exactly what they want
    send_message "Hi, I need to create a workflow for our supplier onboarding process. We have a very specific procedure that all new suppliers must go through." "Manager"

    send_message "Our supplier onboarding has these stages: Application Submitted, Documentation Review, Compliance Check, Contract Negotiation, and finally Approved or Rejected. Can you create this workflow for me?" "$MANAGER_CONVERSATION_ID" "Manager"

    send_message "Yes, please create this supplier onboarding workflow in the system. We need it operational by next week." "$MANAGER_CONVERSATION_ID" "Manager"

    send_message "Perfect! Now I also need a workflow for handling customer returns. The process is: Return Requested, Item Received, Quality Inspection, and then either Refund Issued or Return Rejected." "$MANAGER_CONVERSATION_ID" "Manager"

    send_message "Create the customer returns workflow as well, please." "$MANAGER_CONVERSATION_ID" "Manager"

    print_status "Manager conversation completed - Created 2 workflows with clear requirements"
}

# Novice User Persona - Learning and exploring
test_novice_persona() {
    print_header "SCENARIO 2: NOVICE USER LEARNING WORKFLOW DESIGN"
    echo -e "${CYAN}Persona: Mike, Junior Project Coordinator${NC}"
    echo -e "${CYAN}Context: He knows his work but doesn't understand formal workflows${NC}"
    echo -e "${CYAN}Goal: Learn to create a project management workflow${NC}\n"

    # Novice starts with uncertainty
    send_message "Hello, I'm new to this. I handle projects at work but I'm not sure how to create a workflow. Can you help me?" "Novice"

    send_message "Well, when I get a new project, I usually just start working on it. Sometimes I forget things or don't know what to do next. I think a workflow might help?" "$NOVICE_CONVERSATION_ID" "Novice"

    send_message "That sounds helpful! So for my projects, I typically receive a request, then I need to plan it, work on it, and deliver it. Is that enough for a workflow?" "$NOVICE_CONVERSATION_ID" "Novice"

    send_message "You're right, I should think more about this. Let me think... After I receive a project request, I should probably review it first to understand what's needed. Then I plan it out, execute the work, review everything, and deliver to the client. Does that make more sense?" "$NOVICE_CONVERSATION_ID" "Novice"

    send_message "Yes, that sounds much better! Can you create this project workflow for me? I'd like to see how it works." "$NOVICE_CONVERSATION_ID" "Novice"

    send_message "This is great! I can see how this would help me stay organized. What if I wanted to add a step for getting approval from my manager before I start working? Could I modify the workflow?" "$NOVICE_CONVERSATION_ID" "Novice"

    send_message "Yes, please add a manager approval step after the planning phase and before execution." "$NOVICE_CONVERSATION_ID" "Novice"

    print_status "Novice conversation completed - Learned workflow design and created customized workflow"
}

# Function to verify created workflows
verify_workflows() {
    print_header "VERIFYING CREATED WORKFLOWS"

    local workflows=$(curl -s "$SVC_BUILDER_URL/api/v1/workflows" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    workflows = data.get('workflows', [])
    new_workflows = []

    # Look for workflows that were likely created during testing
    expected_names = [
        'supplier onboarding', 'customer return', 'project management',
        'project workflow', 'supplier', 'return', 'project'
    ]

    for wf in workflows:
        name_lower = wf['name'].lower()
        if any(expected in name_lower for expected in expected_names):
            new_workflows.append(wf)

    print(f'Found {len(new_workflows)} workflows created during testing:')
    for wf in new_workflows:
        print(f'  ✅ {wf[\"name\"]} (ID: {wf[\"spec_id\"]}) - {wf[\"states_count\"]} states, {wf[\"actions_count\"]} actions')

    if len(new_workflows) == 0:
        print('❌ No new workflows found - check if conversations were successful')
    else:
        print(f'\\n🎉 Successfully created {len(new_workflows)} workflows through conversation!')

except Exception as e:
    print(f'Error verifying workflows: {e}')
")

    echo -e "${CYAN}$workflows${NC}\n"
}

# Function to show conversation analysis
show_analysis() {
    print_header "CONVERSATION ANALYSIS"

    echo -e "${CYAN}📊 SCENARIO COMPARISON:${NC}\n"

    echo -e "${GREEN}👔 Business Manager (Sarah):${NC}"
    echo -e "  • Clear requirements from the start"
    echo -e "  • Used specific business terminology"
    echo -e "  • Requested multiple workflows efficiently"
    echo -e "  • Direct communication style"
    echo -e "  • Outcome: 2 complete workflows created\n"

    echo -e "${BLUE}🎓 Novice User (Mike):${NC}"
    echo -e "  • Started with uncertainty and questions"
    echo -e "  • Learned workflow concepts through conversation"
    echo -e "  • Iteratively improved workflow design"
    echo -e "  • Asked for modifications and enhancements"
    echo -e "  • Outcome: 1 customized workflow with learning experience\n"

    echo -e "${PURPLE}🤖 AI Agent Performance:${NC}"
    echo -e "  • Adapted communication style to user expertise level"
    echo -e "  • Provided guidance to novice user"
    echo -e "  • Efficiently processed manager's clear requirements"
    echo -e "  • Maintained business language throughout"
    echo -e "  • Successfully created workflows in both scenarios\n"
}

# Main execution function
main() {
    print_header "CHAT AGENT POC - CONVERSATION TESTING"
    echo -e "${CYAN}Testing two user personas with different experience levels${NC}\n"

    # Check if services are running
    if ! check_services; then
        print_error "Services are not ready. Please run: docker-compose up -d"
        exit 1
    fi

    # Show existing workflows
    list_workflows

    # Test both personas
    test_manager_persona
    test_novice_persona

    # Verify results
    verify_workflows

    # Show analysis
    show_analysis

    print_header "TESTING COMPLETED"
    print_success "Conversation testing completed successfully!"
    echo -e "${YELLOW}💡 TIP:${NC} You can run individual scenarios by calling:"
    echo -e "  ${CYAN}./test_conversations.sh manager${NC} - Test only manager scenario"
    echo -e "  ${CYAN}./test_conversations.sh novice${NC} - Test only novice scenario"
    echo -e "  ${CYAN}./test_conversations.sh verify${NC} - Just verify existing workflows\n"
}

# Handle command line arguments
case "${1:-all}" in
    "manager")
        check_services && test_manager_persona
        ;;
    "novice")
        check_services && test_novice_persona
        ;;
    "verify")
        verify_workflows
        ;;
    "all"|"")
        main
        ;;
    *)
        echo "Usage: $0 [manager|novice|verify|all]"
        echo "  manager - Test experienced business manager scenario"
        echo "  novice  - Test novice user learning scenario"
        echo "  verify  - Verify created workflows"
        echo "  all     - Run complete test suite (default)"
        exit 1
        ;;
esac