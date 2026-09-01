#!/usr/bin/env bash
set -euo pipefail

echo ""
echo "🧪 Rodando testes e checando cobertura antes do push..."
echo ""

if ! make test; then
  echo ""
  echo "❌ Testes ou cobertura falharam! Corrija os erros e tente novamente."
  echo ""
  exit 1
fi

echo ""
echo "✅ Testes passaram e a cobertura está ok! Continuando com o seu push..."
echo ""
