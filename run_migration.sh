#!/bin/bash
# 🚨 Script de emergencia para ejecutar migración de timezone

echo "🚨 EJECUTANDO MIGRACIÓN CRÍTICA DE TIMEZONE"
echo "=========================================="

# Verificar que existe el archivo
if [ ! -f "fix_timezone_migration.py" ]; then
    echo "❌ Error: fix_timezone_migration.py no encontrado"
    exit 1
fi

# Ejecutar migración
echo "⚡ Iniciando migración..."
python fix_timezone_migration.py

if [ $? -eq 0 ]; then
    echo "✅ Migración completada exitosamente"
    echo "🔄 Ahora puedes reiniciar el servidor para aplicar los cambios"
else
    echo "❌ Error en la migración"
    exit 1
fi