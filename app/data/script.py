import json
import os


def merge_questionnaire_parts():
    """
    Combina múltiples archivos JSON del cuestionario en un solo archivo completo.

    Esta función asume que los archivos tienen un patrón de nombre específico
    y están ubicados en el directorio actual.
    """
    # Definir la ruta de salida
    output_file = "questionnaire_complete.json"

    # Inicializar el objeto base que contendrá todo
    complete_data = {
        "introduction": {},
        "sectors": [],
        "subsectors": {},
        "common_intro": "",
        "technical_intro": "",
        "objectives_intro": "",
        "constraints_intro": "",
        "budget_intro": "",
        "questions": {},
        "facts": {},
        "proposal_template": {},
    }

    # Buscar todos los archivos JSON que coincidan con el patrón
    for i in range(1, 10):  # Asumimos que puede haber hasta 10 partes
        filename = f"questionnaire-json-complete-{i}.json"

        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as file:
                    part_data = json.load(file)

                    # Combinar datos basándose en la estructura
                    # Para secciones que son diccionarios, actualizamos
                    if "introduction" in part_data and part_data["introduction"]:
                        complete_data["introduction"].update(part_data["introduction"])

                    if "sectors" in part_data and part_data["sectors"]:
                        # Combinar garantizando que no haya duplicados
                        for sector in part_data["sectors"]:
                            if sector not in complete_data["sectors"]:
                                complete_data["sectors"].append(sector)

                    if "subsectors" in part_data and part_data["subsectors"]:
                        for sector, subsectors in part_data["subsectors"].items():
                            if sector not in complete_data["subsectors"]:
                                complete_data["subsectors"][sector] = subsectors
                            else:
                                # Añadir subsectores no duplicados
                                for subsector in subsectors:
                                    if (
                                        subsector
                                        not in complete_data["subsectors"][sector]
                                    ):
                                        complete_data["subsectors"][sector].append(
                                            subsector
                                        )

                    # Para campos de texto, usamos el primer valor no vacío encontrado
                    if (
                        "common_intro" in part_data
                        and part_data["common_intro"]
                        and not complete_data["common_intro"]
                    ):
                        complete_data["common_intro"] = part_data["common_intro"]

                    if (
                        "technical_intro" in part_data
                        and part_data["technical_intro"]
                        and not complete_data["technical_intro"]
                    ):
                        complete_data["technical_intro"] = part_data["technical_intro"]

                    if (
                        "objectives_intro" in part_data
                        and part_data["objectives_intro"]
                        and not complete_data["objectives_intro"]
                    ):
                        complete_data["objectives_intro"] = part_data[
                            "objectives_intro"
                        ]

                    if (
                        "constraints_intro" in part_data
                        and part_data["constraints_intro"]
                        and not complete_data["constraints_intro"]
                    ):
                        complete_data["constraints_intro"] = part_data[
                            "constraints_intro"
                        ]

                    if (
                        "budget_intro" in part_data
                        and part_data["budget_intro"]
                        and not complete_data["budget_intro"]
                    ):
                        complete_data["budget_intro"] = part_data["budget_intro"]

                    # Para preguntas y hechos, actualizar los diccionarios
                    if "questions" in part_data and part_data["questions"]:
                        complete_data["questions"].update(part_data["questions"])

                    if "facts" in part_data and part_data["facts"]:
                        complete_data["facts"].update(part_data["facts"])

                    # Para la plantilla de propuesta, usar la primera completa encontrada
                    if (
                        "proposal_template" in part_data
                        and part_data["proposal_template"]
                        and not complete_data["proposal_template"]
                    ):
                        complete_data["proposal_template"] = part_data[
                            "proposal_template"
                        ]

                print(f"Procesado {filename} correctamente")
            except json.JSONDecodeError:
                print(f"Error al decodificar JSON en {filename}")
            except Exception as e:
                print(f"Error al procesar {filename}: {str(e)}")

    # Guardar el archivo combinado
    try:
        with open(output_file, "w", encoding="utf-8") as outfile:
            json.dump(complete_data, outfile, ensure_ascii=False, indent=2)
        print(f"Archivo combinado creado exitosamente: {output_file}")
    except Exception as e:
        print(f"Error al guardar el archivo combinado: {str(e)}")


if __name__ == "__main__":
    merge_questionnaire_parts()
