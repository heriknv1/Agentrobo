"""Native Monaw tool wrappers for Agentrobo Studio. No Cloud API or credentials."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.agent.runtime_paths import WORKSPACE_DIR
from .engine import Studio, StudioError

ROOT = Path(WORKSPACE_DIR) / "Agentrobo-Studio"


def _studio():
    return Studio(ROOT)


def _reply(fn, **kwargs):
    try:
        return json.dumps({"status": "ok", "data": fn(**kwargs)}, ensure_ascii=False)
    except (StudioError, ValueError, OSError, json.JSONDecodeError) as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)


def _json_array(value, what):
    try:
        result = json.loads(value)
    except (TypeError, ValueError):
        raise StudioError(what + " precisa ser um array JSON")
    if not isinstance(result, list):
        raise StudioError(what + " precisa ser um array JSON")
    return result


def studio_create_project(title: str, premise: str, genre: str = "drama",
                          aspect: str = "16:9", daily_limit: int = 50,
                          episode_limit: int = 150) -> str:
    return _reply(_studio().create, title=title, premise=premise, genre=genre,
                  aspect=aspect, daily_limit=daily_limit, episode_limit=episode_limit)


def studio_story_bible(project_id: str, characters_json: str,
                       locations_json: str, season_arc: str) -> str:
    try:
        characters = _json_array(characters_json, "characters_json")
        locations = _json_array(locations_json, "locations_json")
    except StudioError as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)
    return _reply(_studio().bible, project_id=project_id, characters=characters,
                  locations=locations, arc=season_arc)


def studio_plan_episode(project_id: str, episode_number: int, title: str,
                        synopsis: str, scenes_json: str) -> str:
    try:
        scenes = _json_array(scenes_json, "scenes_json")
    except StudioError as exc:
        return json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False)
    return _reply(_studio().episode, project_id=project_id, number=episode_number,
                  title=title, synopsis=synopsis, scenes=scenes)


def studio_project_status(project_id: str) -> str:
    return _reply(_studio().status, project_id=project_id)


def studio_next_scene(project_id: str, episode_number: int = 0) -> str:
    return _reply(_studio().next_scene, project_id=project_id,
                  episode_number=episode_number or None)


def studio_prepare_scene(project_id: str, scene_id: str) -> str:
    return _reply(_studio().prepare, project_id=project_id, scene_id=scene_id)


def studio_record_generation(project_id: str, scene_id: str, confirmed_cost: int,
                             ui_evidence: str, daily_spent: int = 0) -> str:
    return _reply(_studio().record_submitted, project_id=project_id, scene_id=scene_id,
                  confirmed_cost=confirmed_cost, ui_evidence=ui_evidence,
                  daily_spent=daily_spent)


def studio_reconcile_no_charge(project_id: str, scene_id: str, evidence: str) -> str:
    return _reply(_studio().reconcile_not_charged, project_id=project_id,
                  scene_id=scene_id, evidence=evidence)


def studio_import_clip(project_id: str, scene_id: str, file_path: str) -> str:
    return _reply(_studio().import_clip, project_id=project_id, scene_id=scene_id,
                  file_path=file_path)


def studio_review_clip(project_id: str, scene_id: str, approve: bool,
                       notes: str = "") -> str:
    return _reply(_studio().review, project_id=project_id, scene_id=scene_id,
                  approve=approve, notes=notes)


def studio_assemble_episode(project_id: str, episode_number: int) -> str:
    return _reply(_studio().assemble, project_id=project_id,
                  episode_number=episode_number)


def register_tools(registry, _settings=None):
    # Tools are bound to Documents/monaw/Agentrobo-Studio and deliberately have
    # no access to Google credentials or to hidden browser endpoints.
    defs = [
        ("studio_create_project", studio_create_project, "Criar projeto de mininovela 720p.",
         {"title": "string", "premise": "string", "genre": "string", "aspect": "string",
          "daily_limit": "integer", "episode_limit": "integer"}, ["title", "premise"]),
        ("studio_story_bible", studio_story_bible,
         "Definir personagens, aparência, voz, figurino, cenários e arco. Arrays JSON em strings.",
         {"project_id": "string", "characters_json": "string", "locations_json": "string",
          "season_arc": "string"}, ["project_id", "characters_json", "locations_json", "season_arc"]),
        ("studio_plan_episode", studio_plan_episode,
         "Planejar episódio com lista de cenas JSON; somente Veo Lite ou Omni 1.2 a 720p.",
         {"project_id": "string", "episode_number": "integer", "title": "string",
          "synopsis": "string", "scenes_json": "string"},
         ["project_id", "episode_number", "title", "synopsis", "scenes_json"]),
        ("studio_project_status", studio_project_status,
         "Consultar estado e créditos já comprometidos, sem alterar dados.",
         {"project_id": "string"}, ["project_id"]),
        ("studio_next_scene", studio_next_scene,
         "Pegar próxima cena pendente, prompt, custo estimado, duração e modelo.",
         {"project_id": "string", "episode_number": "integer"}, ["project_id"]),
        ("studio_prepare_scene", studio_prepare_scene,
         "Preparar cena e validar orçamento antes de abrir o Google Flow.",
         {"project_id": "string", "scene_id": "string"}, ["project_id", "scene_id"]),
        ("studio_record_generation", studio_record_generation,
         "REGISTRO pós-envio: só depois de observar visualmente no Flow o modelo, 720p, custo e envio. Estado inicial incerto; NUNCA é autorização para gastar. Guardar evidência sem dados privados.",
         {"project_id": "string", "scene_id": "string", "confirmed_cost": "integer",
          "ui_evidence": "string", "daily_spent": "integer"},
         ["project_id", "scene_id", "confirmed_cost", "ui_evidence"]),
        ("studio_reconcile_no_charge", studio_reconcile_no_charge,
         "Liberar tentativa incerta apenas após prova clara de que NÃO houve geração/cobrança no Flow. Não usar em caso de dúvida.",
         {"project_id": "string", "scene_id": "string", "evidence": "string"},
         ["project_id", "scene_id", "evidence"]),
        ("studio_import_clip", studio_import_clip,
         "Importar vídeo já baixado para cena, exigindo resolução nativa exata 1280x720 ou 720x1280 e ffprobe instalado.",
         {"project_id": "string", "scene_id": "string", "file_path": "string"},
         ["project_id", "scene_id", "file_path"]),
        ("studio_review_clip", studio_review_clip,
         "Marcar vídeo como aprovado/rejeitado após avaliação de continuidade e qualidade.",
         {"project_id": "string", "scene_id": "string", "approve": "boolean", "notes": "string"},
         ["project_id", "scene_id", "approve"]),
        ("studio_assemble_episode", studio_assemble_episode,
         "Montar vídeo MP4 720p usando FFmpeg a partir de todas as cenas aprovadas, sem sobrescrever arquivos.",
         {"project_id": "string", "episode_number": "integer"}, ["project_id", "episode_number"]),
    ]
    for name, function, description, fields, required in defs:
        mutates = name not in {"studio_project_status", "studio_next_scene"}
        registry.register({
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {key: {"type": typ} for key, typ in fields.items()},
                "required": required,
            },
            "callable": function,
            "domain": "workspace" if mutates else "general",
            "execution_mode": "sync_stateless",
            "affinity_group": None,
            "metadata": {
                "parallel_safe": not mutates,
                "resource_locks": ["agentrobo_studio_project"] if mutates else [],
                "mutates_state": mutates,
                "risk_level": "medium" if mutates else "low",
                "repeat_safe": not mutates,
            },
        })
