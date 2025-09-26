# Chat Agent PoC - Testing Guide

This guide explains how to test the conversational workflow creation system with two different user personas.

## 🎭 User Personas

### **1. Sarah - Experienced Business Manager**
**Background**: Operations Manager at a logistics company
**Characteristics**:
- Knows exactly what processes she wants to automate
- Uses specific business terminology
- Has clear, detailed requirements
- Efficient communication style
- Creates multiple workflows in one session

**Test Scenario**: Creates supplier onboarding and customer returns workflows

### **2. Mike - Novice User Learning Workflow Design**
**Background**: Junior Project Coordinator new to formal processes
**Characteristics**:
- Understands his daily work but not formal workflows
- Needs guidance and explanation
- Learns through conversation
- Iteratively improves his understanding
- Asks questions and requests modifications

**Test Scenario**: Creates and modifies a project management workflow

## 🚀 Running the Tests

### **Option 1: Interactive Test Menu**
```bash
./run_tests.sh
```

This provides a user-friendly menu with options:
1. Test Experienced Business Manager
2. Test Novice User
3. Run Full Conversation Test Suite
4. Verify Existing Workflows
5. Quick Health Check
6. Manual Chat Test

### **Option 2: Direct Script Execution**
```bash
# Run complete test suite (both personas)
./test_conversations.sh all

# Test only the business manager scenario
./test_conversations.sh manager

# Test only the novice user scenario
./test_conversations.sh novice

# Just verify workflows in the system
./test_conversations.sh verify
```

## 📊 Expected Test Results

### **Business Manager Test (Sarah)**
**Expected Workflows Created**:
1. **Supplier Onboarding Workflow**
   - States: Application Submitted → Documentation Review → Compliance Check → Contract Negotiation → Approved/Rejected
   - Actions: Submit Application, Review Documents, Check Compliance, Negotiate Contract

2. **Customer Returns Workflow**
   - States: Return Requested → Item Received → Quality Inspection → Refund Issued/Return Rejected
   - Actions: Request Return, Receive Item, Inspect Quality, Process Decision

**Conversation Characteristics**:
- Direct, professional communication
- Clear requirements stated upfront
- Efficient workflow creation
- Multiple workflows in one session

### **Novice User Test (Mike)**
**Expected Workflows Created**:
1. **Project Management Workflow** (with iterations)
   - Initial: Request Received → Planning → Execution → Delivery
   - Enhanced: Request Received → Review → Planning → Manager Approval → Execution → Review → Delivery

**Conversation Characteristics**:
- Starts with uncertainty
- Learns workflow concepts during conversation
- Requests clarification and guidance
- Iteratively improves workflow design
- Asks for modifications

## 🔍 Test Verification

After running tests, the script will:

1. **Health Check**: Verify all services are running
2. **Conversation Simulation**: Execute realistic user interactions
3. **Workflow Verification**: Check that workflows were actually created in the system
4. **Analysis Report**: Compare how the AI handled both user types

### **Verification Commands**
```bash
# Check created workflows
curl http://localhost:8000/api/v1/workflows

# View specific workflow details
curl http://localhost:8000/api/v1/workflows/wf_supplier_onboarding
curl http://localhost:8000/api/v1/workflows/wf_customer_returns
curl http://localhost:8000/api/v1/workflows/wf_project_management
```

## 🎯 What the Tests Demonstrate

### **AI Adaptability**
- **With Experienced Users**: Direct, efficient processing of clear requirements
- **With Novice Users**: Patient guidance, educational responses, iterative building

### **Business Language Processing**
- Converts natural business language to technical specifications
- Maintains business terminology throughout conversations
- Never exposes technical JSON or validation details

### **Workflow Auto-Generation**
- Creates complete workflow specifications from conversation
- Generates appropriate state names, action slugs, and permissions
- Handles both simple and complex workflow structures

### **Conversation Management**
- Maintains context across multiple messages
- Supports workflow modifications and enhancements
- Handles different communication styles appropriately

## 🔧 Troubleshooting Tests

### **Common Issues**

**Services Not Running**:
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs if needed
docker-compose logs ai-agent
```

**Test Script Permissions**:
```bash
# Make scripts executable
chmod +x test_conversations.sh
chmod +x run_tests.sh
```

**No Workflows Created**:
- Check that all services are healthy
- Verify MCP server is connected to svc-builder
- Check AI agent logs for any errors

### **Manual Verification**
If automated tests don't work, you can manually test:

```bash
# Test AI Agent directly
curl -X POST "http://localhost:8001/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need a simple workflow for task management"}'

# Check workflows were created
curl http://localhost:8000/api/v1/workflows
```

## 📈 Performance Expectations

**Typical Test Duration**:
- Manager scenario: ~2-3 minutes
- Novice scenario: ~3-4 minutes
- Full test suite: ~5-7 minutes

**Expected Outcomes**:
- 2-3 new workflows created during testing
- Clear conversation logs showing AI adaptation
- Verification that all workflows are properly structured
- Analysis showing different interaction patterns

## 🎉 Success Criteria

The tests are successful if:
- ✅ All services respond to health checks
- ✅ Both personas complete their conversations
- ✅ Workflows are created and stored in the system
- ✅ AI maintains business language throughout
- ✅ Technical specifications are properly generated
- ✅ Different user types receive appropriate responses

---

**Ready to test? Run `./run_tests.sh` and select your preferred testing scenario!**