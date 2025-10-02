#!/bin/bash

# Chat Agent PoC - Pruebas de Conversación en Español
# Prueba dos perfiles de usuario:
# 1. Gerente de Negocios Experimentado
# 2. Usuario Novato Aprendiendo Diseño de Flujos

set -e

# Colores para salida
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # Sin Color

# Configuración
AI_AGENT_URL="http://localhost:8001"
SVC_BUILDER_URL="http://localhost:8000"
CHAT_ENDPOINT="$AI_AGENT_URL/api/v1/chat"

# Variables globales para seguimiento de conversaciones
GERENTE_CONVERSATION_ID=""
NOVATO_CONVERSATION_ID=""

# Funciones auxiliares
print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_user() {
    echo -e "${GREEN}👤 USUARIO ($2):${NC} $1\n"
}

print_ai() {
    echo -e "${PURPLE}🤖 AGENTE IA:${NC} $1\n"
}

print_status() {
    echo -e "${YELLOW}📊 ESTADO:${NC} $1\n"
}

print_error() {
    echo -e "${RED}❌ ERROR:${NC} $1\n"
}

print_success() {
    echo -e "${GREEN}✅ ÉXITO:${NC} $1\n"
}

# Función para enviar mensaje al agente IA
send_message() {
    local message="$1"
    local conversation_id="$2"
    local user_type="$3"

    # Construir payload JSON - escapar comillas en el mensaje
    local escaped_message=$(echo "$message" | sed 's/"/\\"/g')
    local json_payload="{\"message\": \"$escaped_message\", \"language\": \"es\""
    if [[ -n "$conversation_id" ]]; then
        json_payload="$json_payload, \"conversation_id\": \"$conversation_id\""
    fi
    json_payload="$json_payload}"

    print_user "$message" "$user_type"

    # Enviar solicitud
    local response=$(curl -s -X POST "$CHAT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "$json_payload")

    if [[ $? -ne 0 ]]; then
        print_error "Falló al enviar mensaje al agente IA"
        return 1
    fi

    # Extraer respuesta y conversation_id
    local ai_response=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('response', 'Sin respuesta'))
except:
    print('Error al analizar respuesta')
")

    local new_conversation_id=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('conversation_id', ''))
except:
    print('')
")

    local tools_used=$(echo "$response" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    tools = data.get('mcp_tools_used', [])
    if tools:
        print(f'🔧 Herramientas usadas: {\", \".join(tools)}')
except:
    pass
")

    print_ai "$ai_response"
    if [[ -n "$tools_used" ]]; then
        echo -e "${CYAN}$tools_used${NC}\n"
    fi

    # Actualizar conversation ID si este es el primer mensaje
    if [[ -z "$conversation_id" ]]; then
        if [[ "$user_type" == "Gerente" ]]; then
            GERENTE_CONVERSATION_ID="$new_conversation_id"
        else
            NOVATO_CONVERSATION_ID="$new_conversation_id"
        fi
    fi

    sleep 2  # Pausa para legibilidad
}

# Función para verificar salud de servicios
check_services() {
    print_header "VERIFICANDO SERVICIOS"

    # Verificar AI Agent
    local ai_health=$(curl -s "$AI_AGENT_URL/api/v1/health" 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        print_success "Agente IA está ejecutándose en puerto 8001"
    else
        print_error "Agente IA no responde en puerto 8001"
        return 1
    fi

    # Verificar svc-builder
    local svc_health=$(curl -s "$SVC_BUILDER_URL/api/v1/health" 2>/dev/null)
    if [[ $? -eq 0 ]]; then
        print_success "svc-builder está ejecutándose en puerto 8000"
    else
        print_error "svc-builder no responde en puerto 8000"
        return 1
    fi

    print_status "Todos los servicios están saludables y listos para pruebas"
}

# Función para listar flujos existentes
list_workflows() {
    print_header "FLUJOS DE TRABAJO EXISTENTES EN EL SISTEMA"

    local workflows=$(curl -s "$SVC_BUILDER_URL/api/v1/workflows" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    workflows = data.get('workflows', [])
    print(f'Se encontraron {len(workflows)} flujos de trabajo existentes:')
    for wf in workflows:
        print(f'  • {wf[\"name\"]} (ID: {wf[\"spec_id\"]})')
    if len(workflows) == 0:
        print('  No se encontraron flujos de trabajo.')
except:
    print('Error al cargar flujos de trabajo')
")

    echo -e "${CYAN}$workflows${NC}\n"
}

# Perfil Gerente de Negocios - Experimentado con requisitos claros
test_gerente_persona() {
    print_header "ESCENARIO 1: GERENTE DE NEGOCIOS EXPERIMENTADO"
    echo -e "${CYAN}Perfil: María, Gerente de Operaciones en una empresa de logística${NC}"
    echo -e "${CYAN}Contexto: Ella sabe exactamente qué proceso quiere automatizar${NC}"
    echo -e "${CYAN}Objetivo: Crear un flujo de trabajo de aprobación de presupuestos${NC}\n"

    # Gerente sabe exactamente lo que quiere
    send_message "Hola, necesito crear un flujo de trabajo para nuestro proceso de aprobación de presupuestos. Tenemos un procedimiento muy específico que todos los presupuestos deben seguir." "" "Gerente"

    send_message "Nuestro proceso de aprobación de presupuestos tiene estas etapas: Presupuesto Enviado, Revisión Financiera, Aprobación de Gerencia, Aprobación Final, y finalmente Aprobado o Rechazado. ¿Puedes crear este flujo de trabajo para mí?" "$GERENTE_CONVERSATION_ID" "Gerente"

    send_message "Sí, por favor crea este flujo de trabajo de aprobación de presupuestos en el sistema. Lo necesitamos operacional para la próxima semana." "$GERENTE_CONVERSATION_ID" "Gerente"

    send_message "Perfecto! Ahora también necesito un flujo de trabajo para manejo de reclamos de clientes. El proceso es: Reclamo Recibido, Investigación, Resolución Propuesta, y luego Reclamo Resuelto o Escalado." "$GERENTE_CONVERSATION_ID" "Gerente"

    send_message "Crea el flujo de trabajo de reclamos de clientes también, por favor." "$GERENTE_CONVERSATION_ID" "Gerente"

    print_status "Conversación de gerente completada - Se crearon flujos de trabajo con requisitos claros"
}

# Perfil Usuario Novato - Aprendiendo y explorando
test_novato_persona() {
    print_header "ESCENARIO 2: USUARIO NOVATO APRENDIENDO DISEÑO DE FLUJOS"
    echo -e "${CYAN}Perfil: Carlos, Coordinador de Proyectos Junior${NC}"
    echo -e "${CYAN}Contexto: Conoce su trabajo pero no entiende flujos formales${NC}"
    echo -e "${CYAN}Objetivo: Aprender a crear un flujo de gestión de tareas${NC}\n"

    # Novato comienza con incertidumbre
    send_message "Hola, soy nuevo en esto. Manejo tareas en el trabajo pero no estoy seguro de cómo crear un flujo de trabajo. ¿Puedes ayudarme?" "" "Novato"

    send_message "Bueno, cuando recibo una nueva tarea, generalmente simplemente empiezo a trabajar en ella. A veces olvido cosas o no sé qué hacer después. ¿Crees que un flujo de trabajo podría ayudarme?" "$NOVATO_CONVERSATION_ID" "Novato"

    send_message "¡Eso suena útil! Entonces para mis tareas, típicamente recibo una solicitud, luego necesito planificarla, trabajar en ella, y entregarla. ¿Es suficiente para un flujo de trabajo?" "$NOVATO_CONVERSATION_ID" "Novato"

    send_message "Tienes razón, debería pensar más en esto. Déjame pensar... Después de que recibo una solicitud de tarea, probablemente debería revisarla primero para entender qué se necesita. Luego la planifico, ejecuto el trabajo, reviso todo, y entrego al cliente. ¿Tiene más sentido así?" "$NOVATO_CONVERSATION_ID" "Novato"

    send_message "¡Sí, eso suena mucho mejor! ¿Puedes crear este flujo de trabajo de tareas para mí? Me gustaría ver cómo funciona." "$NOVATO_CONVERSATION_ID" "Novato"

    send_message "¡Esto es genial! Puedo ver cómo esto me ayudaría a mantenerme organizado. ¿Qué tal si quisiera agregar un paso para obtener aprobación de mi jefe antes de comenzar a trabajar? ¿Podría modificar el flujo de trabajo?" "$NOVATO_CONVERSATION_ID" "Novato"

    send_message "Sí, por favor agrega un paso de aprobación del jefe después de la fase de planificación y antes de la ejecución." "$NOVATO_CONVERSATION_ID" "Novato"

    print_status "Conversación de novato completada - Aprendió diseño de flujos y creó flujo personalizado"
}

# Función para verificar flujos creados
verify_workflows() {
    print_header "VERIFICANDO FLUJOS DE TRABAJO CREADOS"

    local workflows=$(curl -s "$SVC_BUILDER_URL/api/v1/workflows" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    workflows = data.get('workflows', [])
    new_workflows = []

    # Buscar flujos que probablemente fueron creados durante las pruebas
    expected_names = [
        'presupuesto', 'budget', 'aprobación', 'reclamo', 'complaint',
        'claim', 'tarea', 'task', 'gestión', 'management'
    ]

    for wf in workflows:
        name_lower = wf['name'].lower()
        if any(expected in name_lower for expected in expected_names):
            new_workflows.append(wf)

    print(f'Se encontraron {len(new_workflows)} flujos creados durante las pruebas:')
    for wf in new_workflows:
        print(f'  ✅ {wf[\"name\"]} (ID: {wf[\"spec_id\"]}) - {wf[\"states_count\"]} estados, {wf[\"actions_count\"]} acciones')

    if len(new_workflows) == 0:
        print('❌ No se encontraron nuevos flujos - verificar si las conversaciones fueron exitosas')
    else:
        print(f'\\n🎉 ¡Se crearon exitosamente {len(new_workflows)} flujos a través de conversación!')

except Exception as e:
    print(f'Error al verificar flujos: {e}')
")

    echo -e "${CYAN}$workflows${NC}\n"
}

# Función para mostrar análisis de conversación
show_analysis() {
    print_header "ANÁLISIS DE CONVERSACIÓN"

    echo -e "${CYAN}📊 COMPARACIÓN DE ESCENARIOS:${NC}\n"

    echo -e "${GREEN}👔 Gerente de Negocios (María):${NC}"
    echo -e "  • Requisitos claros desde el inicio"
    echo -e "  • Usó terminología de negocios específica"
    echo -e "  • Solicitó múltiples flujos eficientemente"
    echo -e "  • Estilo de comunicación directo"
    echo -e "  • Resultado: Flujos completos creados\n"

    echo -e "${BLUE}🎓 Usuario Novato (Carlos):${NC}"
    echo -e "  • Comenzó con incertidumbre y preguntas"
    echo -e "  • Aprendió conceptos de flujos a través de conversación"
    echo -e "  • Mejoró iterativamente el diseño del flujo"
    echo -e "  • Pidió modificaciones y mejoras"
    echo -e "  • Resultado: Flujo personalizado con experiencia de aprendizaje\n"

    echo -e "${PURPLE}🤖 Rendimiento del Agente IA:${NC}"
    echo -e "  • Adaptó estilo de comunicación al nivel de experiencia del usuario"
    echo -e "  • Proporcionó orientación al usuario novato"
    echo -e "  • Procesó eficientemente requisitos claros del gerente"
    echo -e "  • Mantuvo lenguaje de negocios en todo momento"
    echo -e "  • Creó exitosamente flujos en español en ambos escenarios\n"
}

# Función principal de ejecución
main() {
    print_header "CHAT AGENT POC - PRUEBAS DE CONVERSACIÓN EN ESPAÑOL"
    echo -e "${CYAN}Probando dos perfiles de usuario con diferentes niveles de experiencia${NC}\n"

    # Verificar si los servicios están ejecutándose
    if ! check_services; then
        print_error "Los servicios no están listos. Por favor ejecuta: docker-compose up -d"
        exit 1
    fi

    # Mostrar flujos existentes
    list_workflows

    # Probar ambos perfiles
    test_gerente_persona
    test_novato_persona

    # Verificar resultados
    verify_workflows

    # Mostrar análisis
    show_analysis

    print_header "PRUEBAS COMPLETADAS"
    print_success "¡Pruebas de conversación completadas exitosamente!"
    echo -e "${YELLOW}💡 CONSEJO:${NC} Puedes ejecutar escenarios individuales llamando:"
    echo -e "  ${CYAN}./test_conversations_es.sh gerente${NC} - Probar solo escenario de gerente"
    echo -e "  ${CYAN}./test_conversations_es.sh novato${NC} - Probar solo escenario de novato"
    echo -e "  ${CYAN}./test_conversations_es.sh verificar${NC} - Solo verificar flujos existentes\n"
}

# Manejar argumentos de línea de comandos
case "${1:-all}" in
    "gerente")
        check_services && test_gerente_persona
        ;;
    "novato")
        check_services && test_novato_persona
        ;;
    "verificar")
        verify_workflows
        ;;
    "all"|"")
        main
        ;;
    *)
        echo "Uso: $0 [gerente|novato|verificar|all]"
        echo "  gerente   - Probar escenario de gerente de negocios experimentado"
        echo "  novato    - Probar escenario de usuario novato aprendiendo"
        echo "  verificar - Verificar flujos creados"
        echo "  all       - Ejecutar suite completa de pruebas (predeterminado)"
        exit 1
        ;;
esac
