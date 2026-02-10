import json
import csv
from typing import Any, List, Dict, Tuple
from pathlib import Path


def normalizar_valor(valor: Any) -> Any:
    """
    Normaliza valores para comparação (converte tipos similares)
    """
    if isinstance(valor, (int, float)):
        return float(valor) if isinstance(valor, float) or isinstance(valor, int) else valor
    return valor


def ordenar_lista(lista: List[Any]) -> List[Any]:
    """
    Ordena uma lista recursivamente para comparação
    """
    if not isinstance(lista, list):
        return lista
    
    resultado = []
    for item in lista:
        if isinstance(item, dict):
            # Ordena dicionários por chaves e valores recursivamente
            item_ordenado = {}
            for chave in sorted(item.keys()):
                if isinstance(item[chave], list):
                    item_ordenado[chave] = ordenar_lista(item[chave])
                elif isinstance(item[chave], dict):
                    item_ordenado[chave] = ordenar_dicionario(item[chave])
                else:
                    item_ordenado[chave] = item[chave]
            resultado.append(item_ordenado)
        elif isinstance(item, list):
            resultado.append(ordenar_lista(item))
        else:
            resultado.append(item)
    
    # Tenta ordenar a lista se todos os itens são comparáveis
    try:
        return sorted(resultado, key=lambda x: json.dumps(x, sort_keys=True) if isinstance(x, (dict, list)) else x)
    except TypeError:
        # Se não conseguir ordenar, retorna como está
        return resultado


def ordenar_dicionario(dic: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ordena um dicionário recursivamente
    """
    resultado = {}
    for chave in sorted(dic.keys()):
        valor = dic[chave]
        if isinstance(valor, list):
            resultado[chave] = ordenar_lista(valor)
        elif isinstance(valor, dict):
            resultado[chave] = ordenar_dicionario(valor)
        else:
            resultado[chave] = valor
    return resultado


def obter_tipo(valor: Any) -> str:
    """
    Retorna o tipo do valor como string
    """
    if valor is None:
        return "None"
    tipo = type(valor).__name__
    if tipo == "int":
        return "int"
    elif tipo == "float":
        return "float"
    elif tipo == "str":
        return "str"
    elif tipo == "bool":
        return "bool"
    elif tipo == "list":
        return "list"
    elif tipo == "dict":
        return "dict"
    return tipo


def comparar_valores(valor1: Any, valor2: Any, caminho: str = "") -> List[Dict[str, str]]:
    """
    Compara dois valores e retorna lista de diferenças
    """
    diferencas = []
    
    tipo1 = obter_tipo(valor1)
    tipo2 = obter_tipo(valor2)
    
    # Verifica se os tipos são diferentes
    if tipo1 != tipo2:
        diferencas.append({
            "caminho": caminho,
            "tipo_diferenca": "TIPO_DIFERENTE",
            "valor_json1": str(valor1),
            "tipo_json1": tipo1,
            "valor_json2": str(valor2) if valor2 is not None else "CAMPO_NAO_EXISTE",
            "tipo_json2": tipo2,
            "detalhes": f"Tipos diferentes: {tipo1} vs {tipo2}"
        })
        return diferencas
    
    # Se são listas, compara recursivamente
    if isinstance(valor1, list):
        lista1_ordenada = ordenar_lista(valor1)
        lista2_ordenada = ordenar_lista(valor2)
        
        # Verifica quantidade de itens
        if len(lista1_ordenada) != len(lista2_ordenada):
            diferencas.append({
                "caminho": caminho,
                "tipo_diferenca": "QUANTIDADE_ITENS_DIFERENTE",
                "valor_json1": f"Lista com {len(lista1_ordenada)} itens",
                "tipo_json1": "list",
                "valor_json2": f"Lista com {len(lista2_ordenada)} itens",
                "tipo_json2": "list",
                "detalhes": f"Quantidade diferente: {len(lista1_ordenada)} vs {len(lista2_ordenada)}"
            })
        
        # Compara cada item da lista
        max_len = max(len(lista1_ordenada), len(lista2_ordenada))
        for i in range(max_len):
            novo_caminho = f"{caminho}[{i}]"
            if i < len(lista1_ordenada) and i < len(lista2_ordenada):
                diferencas.extend(comparar_valores(lista1_ordenada[i], lista2_ordenada[i], novo_caminho))
            elif i < len(lista1_ordenada):
                diferencas.append({
                    "caminho": novo_caminho,
                    "tipo_diferenca": "ITEM_AUSENTE_JSON2",
                    "valor_json1": str(lista1_ordenada[i]),
                    "tipo_json1": obter_tipo(lista1_ordenada[i]),
                    "valor_json2": "ITEM_NAO_EXISTE",
                    "tipo_json2": "N/A",
                    "detalhes": "Item existe no JSON1 mas não no JSON2"
                })
            else:
                diferencas.append({
                    "caminho": novo_caminho,
                    "tipo_diferenca": "ITEM_AUSENTE_JSON1",
                    "valor_json1": "ITEM_NAO_EXISTE",
                    "tipo_json1": "N/A",
                    "valor_json2": str(lista2_ordenada[i]),
                    "tipo_json2": obter_tipo(lista2_ordenada[i]),
                    "detalhes": "Item existe no JSON2 mas não no JSON1"
                })
    
    # Se são dicionários, compara recursivamente
    elif isinstance(valor1, dict):
        chaves1 = set(valor1.keys())
        chaves2 = set(valor2.keys())
        
        # Campos que existem no JSON1 mas não no JSON2
        chaves_apenas_json1 = chaves1 - chaves2
        for chave in chaves_apenas_json1:
            novo_caminho = f"{caminho}.{chave}" if caminho else chave
            diferencas.append({
                "caminho": novo_caminho,
                "tipo_diferenca": "CAMPO_AUSENTE_JSON2",
                "valor_json1": str(valor1[chave]),
                "tipo_json1": obter_tipo(valor1[chave]),
                "valor_json2": "CAMPO_NAO_EXISTE",
                "tipo_json2": "N/A",
                "detalhes": "Campo existe no JSON1 mas não no JSON2"
            })
        
        # Compara campos comuns
        chaves_comuns = chaves1 & chaves2
        for chave in chaves_comuns:
            novo_caminho = f"{caminho}.{chave}" if caminho else chave
            diferencas.extend(comparar_valores(valor1[chave], valor2[chave], novo_caminho))
    
    # Para valores primitivos, compara diretamente
    else:
        valor1_norm = normalizar_valor(valor1)
        valor2_norm = normalizar_valor(valor2)
        
        if valor1_norm != valor2_norm:
            diferencas.append({
                "caminho": caminho,
                "tipo_diferenca": "VALOR_DIFERENTE",
                "valor_json1": str(valor1),
                "tipo_json1": tipo1,
                "valor_json2": str(valor2),
                "tipo_json2": tipo2,
                "detalhes": f"Valores diferentes: {valor1} vs {valor2}"
            })
    
    return diferencas


def comparar_json(json1: Dict[str, Any], json2: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Compara dois objetos JSON e retorna lista de diferenças
    """
    diferencas = []
    
    # Ordena ambos os JSONs para comparação consistente
    json1_ordenado = ordenar_dicionario(json1)
    json2_ordenado = ordenar_dicionario(json2)
    
    # Compara recursivamente
    diferencas.extend(comparar_valores(json1_ordenado, json2_ordenado, ""))
    
    return diferencas


def salvar_diferencas_csv(diferencas: List[Dict[str, str]], arquivo_saida: str):
    """
    Salva as diferenças em um arquivo CSV
    """
    if not diferencas:
        print("Nenhuma diferença encontrada!")
        return
    
    campos = ["caminho", "tipo_diferenca", "valor_json1", "tipo_json1", "valor_json2", "tipo_json2", "detalhes"]
    
    with open(arquivo_saida, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=campos)
        writer.writeheader()
        writer.writerows(diferencas)
    
    print(f"Diferenças salvas em: {arquivo_saida}")
    print(f"Total de diferenças encontradas: {len(diferencas)}")


def main():
    """
    Função principal
    """
    import sys
    
    # Solicita os caminhos dos arquivos JSON
    if len(sys.argv) >= 3:
        arquivo_json1 = sys.argv[1]
        arquivo_json2 = sys.argv[2]
        arquivo_saida = sys.argv[3] if len(sys.argv) >= 4 else "diferencas.csv"
    else:
        arquivo_json1 = input("Digite o caminho do primeiro arquivo JSON: ").strip()
        arquivo_json2 = input("Digite o caminho do segundo arquivo JSON: ").strip()
        arquivo_saida = input("Digite o nome do arquivo CSV de saída (padrão: diferencas.csv): ").strip()
        if not arquivo_saida:
            arquivo_saida = "diferencas.csv"
    
    # Garante que o arquivo de saída tenha extensão .csv
    if not arquivo_saida.endswith('.csv'):
        arquivo_saida += '.csv'
    
    try:
        # Carrega os arquivos JSON
        print(f"Carregando {arquivo_json1}...")
        with open(arquivo_json1, 'r', encoding='utf-8') as f:
            json1 = json.load(f)
        
        print(f"Carregando {arquivo_json2}...")
        with open(arquivo_json2, 'r', encoding='utf-8') as f:
            json2 = json.load(f)
        
        print("Comparando JSONs...")
        diferencas = comparar_json(json1, json2)
        
        # Salva as diferenças no CSV
        salvar_diferencas_csv(diferencas, arquivo_saida)
        
        # Exibe resumo
        if diferencas:
            print("\n=== RESUMO DAS DIFERENÇAS ===")
            tipos_diferenca = {}
            for diff in diferencas:
                tipo = diff["tipo_diferenca"]
                tipos_diferenca[tipo] = tipos_diferenca.get(tipo, 0) + 1
            
            for tipo, quantidade in tipos_diferenca.items():
                print(f"{tipo}: {quantidade}")
        else:
            print("\n✓ Nenhuma diferença encontrada! Os JSONs são idênticos.")
    
    except FileNotFoundError as e:
        print(f"Erro: Arquivo não encontrado - {e}")
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")


if __name__ == "__main__":
    main()

