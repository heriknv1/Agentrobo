"""Agentrobo Studio: local project, scene, 720p and credit state.

No Google credentials, network calls, browser automation or purchases live here.
The real browser uses the Monaw Chrome extension under its existing approval gates.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path

MODELS = {"veo-3.1-lite", "omni-flash-1.2"}
FEATURES = {"text_to_video", "frames_to_video", "ingredients_to_video"}
STATUSES = {"planned", "prepared", "submitted", "uncertain", "generated", "approved", "rejected"}
SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")


class StudioError(ValueError):
    pass


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def price(model: str, seconds: int, feature: str = "text_to_video") -> int:
    if model not in MODELS:
        raise StudioError("Modelo proibido: use veo-3.1-lite ou omni-flash-1.2")
    if feature not in FEATURES:
        raise StudioError("Tipo de geração desconhecido")
    if model == "veo-3.1-lite":
        if seconds not in {4, 6, 8}:
            raise StudioError("Veo 3.1 Lite só permite 4, 6 ou 8 segundos")
        if feature == "ingredients_to_video" and seconds != 8:
            raise StudioError("Veo Lite com referências requer 8 segundos")
        return 10  # Standard/non-Ultra pricing. Actual Flow UI is authoritative.
    if not isinstance(seconds, int) or not 3 <= seconds <= 10:
        raise StudioError("Omni Flash 1.2 gratuito permite 3 a 10 segundos")
    return seconds * 3  # 720p; never offer 360p or unsupported extension.


def _text(value, field, limit=6000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise StudioError("Campo inválido: " + field)
    return value.strip()


def _id(value):
    if not isinstance(value, str) or not SLUG_RE.fullmatch(value):
        raise StudioError("Identificador inválido")
    return value


def _atomic_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class Studio:
    def __init__(self, root: Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id):
        return self.root / _id(project_id)

    def _load(self, project_id):
        path = self._path(project_id) / "project.json"
        if not path.is_file():
            raise StudioError("Projeto não encontrado")
        return json.loads(path.read_text(encoding="utf-8"))

    @contextlib.contextmanager
    def _edit(self, project_id):
        folder = self._path(project_id)
        lock = folder / ".edit.lock"
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise StudioError("Projeto ocupado por outra operação. Revise antes de repetir.")
        try:
            os.write(fd, (str(os.getpid()) + " " + _now()).encode("utf-8"))
            os.close(fd)
            project = self._load(project_id)
            yield project
            project["updated_at"] = _now()
            _atomic_json(folder / "project.json", project)
        finally:
            lock.unlink(missing_ok=True)

    def create(self, title, premise, genre="drama", aspect="16:9", daily_limit=50, episode_limit=150):
        _text(title, "título", 160)
        _text(premise, "premissa")
        if aspect not in {"16:9", "9:16"}:
            raise StudioError("Proporção: 16:9 ou 9:16")
        if not 1 <= int(daily_limit) <= 100000 or not 1 <= int(episode_limit) <= 100000:
            raise StudioError("Limite de créditos inválido")
        project_id = "serie-" + secrets.token_hex(5)
        folder = self._path(project_id)
        folder.mkdir(mode=0o700)
        (folder / "referencias").mkdir()
        (folder / "episodios").mkdir()
        state = {
            "schema": 1, "id": project_id, "title": title.strip(), "premise": premise.strip(),
            "genre": _text(genre, "gênero", 80), "aspect": aspect, "resolution": "720p",
            "allowed_models": sorted(MODELS), "daily_limit": int(daily_limit),
            "episode_limit": int(episode_limit), "characters": [],
            "locations": [], "season_arc": "", "episodes": [], "created_at": _now(),
            "updated_at": _now()
        }
        _atomic_json(folder / "project.json", state)
        return {"id": project_id, "folder": str(folder), "title": title, "resolution": "720p"}

    def bible(self, project_id, characters, locations, arc):
        if not isinstance(characters, list) or not isinstance(locations, list):
            raise StudioError("Personagens e cenários devem ser listas JSON")
        if not 1 <= len(characters) <= 24 or len(locations) > 30:
            raise StudioError("Informe 1 a 24 personagens e até 30 cenários")
        for item in characters:
            for key in ("id", "name", "appearance", "voice", "wardrobe"):
                _text(item.get(key), "personagem." + key)
            _id(item["id"])
        for item in locations:
            for key in ("id", "description"):
                _text(item.get(key), "cenário." + key)
            _id(item["id"])
        if len(set(c["id"] for c in characters)) != len(characters):
            raise StudioError("IDs de personagem duplicados")
        with self._edit(project_id) as p:
            p["characters"] = characters
            p["locations"] = locations
            p["season_arc"] = _text(arc, "arco da temporada")
        return {"status": "ok", "characters": len(characters), "locations": len(locations)}

    def episode(self, project_id, number, title, synopsis, scenes):
        if not isinstance(number, int) or not 1 <= number <= 999:
            raise StudioError("Número de episódio inválido")
        if not isinstance(scenes, list) or not 1 <= len(scenes) <= 100:
            raise StudioError("Episódio requer 1 a 100 cenas")
        _text(title, "título do episódio", 160)
        _text(synopsis, "sinopse")
        with self._edit(project_id) as p:
            if any(e["number"] == number for e in p["episodes"]):
                raise StudioError("Episódio já existe; não sobrescreva cenas")
            known = {ch["id"] for ch in p["characters"]}
            result = []
            for i, item in enumerate(scenes, 1):
                if not isinstance(item, dict):
                    raise StudioError("Cena precisa ser um objeto JSON")
                model = item.get("model", "veo-3.1-lite")
                duration = item.get("seconds", 8)
                feature = item.get("feature", "text_to_video")
                cost = price(model, duration, feature)
                ids = item.get("characters", [])
                if not isinstance(ids, list) or any(ch not in known for ch in ids):
                    raise StudioError("Cena com IDs de personagens desconhecidos")
                result.append({
                    "id": f"E{number:03d}C{i:03d}",
                    "number": i, "summary": _text(item.get("summary"), "resumo da cena"),
                    "dialogue": str(item.get("dialogue", ""))[:1200],
                    "camera": str(item.get("camera", "cinematic medium shot"))[:400],
                    "characters": ids, "location_id": str(item.get("location_id", ""))[:80],
                    "continuity": str(item.get("continuity", ""))[:1600],
                    "model": model, "seconds": duration, "feature": feature,
                    "aspect": p["aspect"], "resolution": "720p", "expected_credits": cost,
                    "status": "planned", "attempts": [], "media": "", "last_error": "",
                })
            p["episodes"].append({"number": number, "title": title.strip(),
                                  "synopsis": synopsis.strip(), "scenes": result})
        return {"episode": number, "scenes": len(result),
                "estimated_credits_one_pass": sum(s["expected_credits"] for s in result)}

    @staticmethod
    def _scene(project, scene_id):
        for ep in project["episodes"]:
            for scene in ep["scenes"]:
                if scene["id"] == scene_id:
                    return ep, scene
        raise StudioError("Cena não encontrada")

    @staticmethod
    def _committed(project, episode_number=None):
        # Includes uncertain browser results: never automatically release reservations.
        cents = 0
        for ep in project["episodes"]:
            if episode_number is not None and ep["number"] != episode_number:
                continue
            for s in ep["scenes"]:
                cents += sum(at["credits"] for at in s["attempts"] if at["state"] != "proved_not_charged")
        return cents

    def prompt(self, project_id, scene_id):
        p = self._load(project_id)
        ep, s = self._scene(p, scene_id)
        people = [ch for ch in p["characters"] if ch["id"] in s["characters"]]
        place = next((x for x in p["locations"] if x["id"] == s["location_id"]), None)
        character_lines = "\n".join(
            f"- {c['id']}: {c['name']}; appearance: {c['appearance']}; "
            f"wardrobe: {c['wardrobe']}; voice: {c['voice']}" for c in people
        )
        prompt = (
            f"Create ONE coherent {s['seconds']}-second scene for a Brazilian {p['genre']} television "
            f"serial, native 720p, {s['aspect']} aspect ratio. Continuity is mandatory.\n"
            f"SERIES: {p['title']}. EPISODE: {ep['title']}.\n"
            f"STORY: {s['summary']}.\n"
            f"CHARACTERS (keep appearance and wardrobe identical to approved references):\n"
            f"{character_lines or 'No character visible.'}\n"
            f"LOCATION: {(place or {}).get('description', 'as established previously')}.\n"
            f"CAMERA: {s['camera']}.\nCONTINUITY: {s['continuity']}.\n"
            f"Spoken dialogue in Brazilian Portuguese (do not translate): {s['dialogue'] or 'No dialogue.'}\n"
            "Natural performances, consistent lighting, stable facial identity and coherent eyelines. "
            "No character morphing, no duplicate limbs, no unexplained costume changes. "
            "No subtitles or watermarks added by the prompt."
        )
        return {"scene_id": scene_id, "model": s["model"], "feature": s["feature"],
                "seconds": s["seconds"], "resolution": "720p", "aspect": s["aspect"],
                "estimated_credits": s["expected_credits"], "prompt": prompt,
                "flow_url": "https://flow.google.com/"}

    def next_scene(self, project_id, episode_number=None):
        p = self._load(project_id)
        for ep in p["episodes"]:
            if episode_number is not None and ep["number"] != episode_number:
                continue
            for scene in ep["scenes"]:
                if scene["status"] in {"planned", "rejected"}:
                    return self.prompt(project_id, scene["id"])
        return {"status": "no_pending_scenes"}

    def prepare(self, project_id, scene_id):
        data = self.prompt(project_id, scene_id)
        with self._edit(project_id) as p:
            ep, s = self._scene(p, scene_id)
            if s["status"] not in {"planned", "rejected", "prepared"}:
                raise StudioError("Cena já enviada, incerta ou finalizada: reconcilie antes")
            if any(a["state"] == "uncertain" for a in s["attempts"]):
                raise StudioError("Tentativa anterior incerta: verifique o Flow antes de gastar")
            if self._committed(p, ep["number"]) + s["expected_credits"] > p["episode_limit"]:
                raise StudioError("Orçamento do episódio ultrapassado")
            s["status"] = "prepared"
        return dict(data, status="prepared",
                    warning="Revise manualmente custo, modelo, resolução e saldo no Flow antes de gerar.")

    def record_submitted(self, project_id, scene_id, confirmed_cost: int, ui_evidence: str, daily_spent: int = 0):
        _text(ui_evidence, "evidência visível do Flow", 700)
        if not isinstance(confirmed_cost, int) or confirmed_cost < 0:
            raise StudioError("Custo confirmado inválido")
        with self._edit(project_id) as p:
            ep, s = self._scene(p, scene_id)
            if s["status"] != "prepared":
                raise StudioError("Cena não preparada ou já enviada; nunca submeta duas vezes")
            if confirmed_cost != s["expected_credits"]:
                raise StudioError("Custo da interface difere do previsto: revise a tabela de preços")
            if daily_spent < 0 or daily_spent + confirmed_cost > p["daily_limit"]:
                raise StudioError("Limite diário ultrapassado")
            if self._committed(p, ep["number"]) + confirmed_cost > p["episode_limit"]:
                raise StudioError("Limite do episódio ultrapassado")
            s["attempts"].append({"at": _now(), "credits": confirmed_cost,
                                  "state": "uncertain", "evidence": ui_evidence[:700]})
            s["status"] = "uncertain"  # The click/submit alone is not proof of video creation.
        return {"status": "uncertain", "scene_id": scene_id,
                "next": "Inspecione o Flow: clip criado -> importar; comprovadamente não enviado -> reconciliar."}

    def reconcile_not_charged(self, project_id, scene_id, evidence: str):
        _text(evidence, "prova de não cobrança", 700)
        with self._edit(project_id) as p:
            _, s = self._scene(p, scene_id)
            if s["status"] != "uncertain" or not s["attempts"]:
                raise StudioError("Não há geração incerta para reconciliar")
            s["attempts"][-1]["state"] = "proved_not_charged"
            s["attempts"][-1]["evidence"] = evidence[:700]
            s["status"] = "planned"
        return {"status": "planned", "warning": "Confirme no Flow que NÃO houve geração nem cobrança."}

    @staticmethod
    def _probe(path: Path):
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height", "-of", "json", str(path)]
        try:
            output = subprocess.run(cmd, capture_output=True, text=True,
                                    check=True, timeout=30)
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            raise StudioError("Instale FFmpeg/ffprobe e confira o vídeo: " + str(exc))
        values = json.loads(output.stdout).get("streams", [])
        if not values:
            raise StudioError("Arquivo não contém vídeo válido")
        return values[0]["width"], values[0]["height"]

    def import_clip(self, project_id, scene_id, file_path):
        path = Path(file_path).expanduser().resolve(strict=True)
        if not path.is_file() or path.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
            raise StudioError("Informe arquivo de vídeo local suportado")
        p = self._load(project_id)
        _, s = self._scene(p, scene_id)
        size = self._probe(path)
        expected = (1280, 720) if p["aspect"] == "16:9" else (720, 1280)
        if size != expected:
            raise StudioError(f"Clip deve ser 720p nativo, recebido {size}, esperado {expected}")
        with self._edit(project_id) as p:
            ep, s = self._scene(p, scene_id)
            if s["status"] not in {"uncertain", "submitted", "prepared"}:
                raise StudioError("Cena fora da etapa de importação")
            folder = self._path(project_id) / "episodios" / f"E{ep['number']:03d}" / "clipes"
            folder.mkdir(parents=True, exist_ok=True)
            destination = folder / (scene_id + path.suffix.lower())
            if destination.exists():
                raise StudioError("Arquivo dessa cena já existe: nenhuma sobrescrita automática")
            shutil.copy2(path, destination)
            s["media"] = str(destination.relative_to(self._path(project_id)))
            s["status"] = "generated"
            if s["attempts"] and s["attempts"][-1]["state"] == "uncertain":
                s["attempts"][-1]["state"] = "generated"
        return {"scene_id": scene_id, "status": "generated", "file": str(destination),
                "resolution": "720p"}

    def review(self, project_id, scene_id, approve: bool, notes=""):
        with self._edit(project_id) as p:
            _, s = self._scene(p, scene_id)
            if s["status"] not in {"generated", "approved", "rejected"} or not s["media"]:
                raise StudioError("Sem vídeo importado para revisar")
            s["status"] = "approved" if approve else "rejected"
            s["review_notes"] = str(notes)[:1000]
        return {"status": "approved" if approve else "rejected"}

    def status(self, project_id):
        p = self._load(project_id)
        ep_summary = []
        for e in p["episodes"]:
            summary = {"number": e["number"], "title": e["title"],
                       "credits_committed": self._committed(p, e["number"]),
                       "limit": p["episode_limit"],
                       "scenes": [{"id": s["id"], "status": s["status"],
                                   "model": s["model"], "seconds": s["seconds"]}
                                  for s in e["scenes"]]}
            ep_summary.append(summary)
        return {"project_id": p["id"], "title": p["title"],
                "resolution": p["resolution"], "aspect": p["aspect"],
                "allowed_models": p["allowed_models"], "episodes": ep_summary}

    def assemble(self, project_id, episode_number):
        p = self._load(project_id)
        ep = next((e for e in p["episodes"] if e["number"] == episode_number), None)
        if not ep:
            raise StudioError("Episódio não existe")
        if not ep["scenes"] or any(s["status"] != "approved" for s in ep["scenes"]):
            raise StudioError("A montagem requer TODOS os clipes aprovados")
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise StudioError("FFmpeg/ffprobe não encontrados no Windows PATH")
        root = self._path(project_id)
        output_dir = root / "episodios" / f"E{episode_number:03d}"
        files = [root / s["media"] for s in ep["scenes"]]
        if any(not path.is_file() for path in files):
            raise StudioError("Clipes ausentes: confira a pasta do projeto")
        expected = (1280, 720) if p["aspect"] == "16:9" else (720, 1280)
        if any(self._probe(f) != expected for f in files):
            raise StudioError("Todos os vídeos precisam ser 720p nativo")
        # Normalize video/audio independently so concat does not fail on mixed fps/audio.
        intermediate = output_dir / "temporarios"
        intermediate.mkdir(exist_ok=True)
        normalized = []
        for s, original in zip(ep["scenes"], files):
            path = intermediate / (s["id"] + ".mp4")
            if path.exists():
                raise StudioError("Arquivo temporário já existe. Revise antes de substituir.")
            has_audio = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "a",
                 "-show_entries", "stream=index", "-of", "csv=p=0", str(original)],
                capture_output=True, text=True, timeout=30, check=True,
            ).stdout.strip()
            inputs = ["-i", str(original)]
            if not has_audio:
                inputs += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
            cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                   "-y", *inputs, "-t", str(s["seconds"]), "-map", "0:v:0",
                   "-map", "0:a:0" if has_audio else "1:a:0",
                   "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-preset",
                   "veryfast", "-crf", "22", "-c:a", "aac", "-ar", "48000",
                   "-ac", "2", "-shortest", "-movflags", "+faststart", str(path)]
            subprocess.run(cmd, check=True, timeout=180)
            normalized.append(path)
        manifest = output_dir / "temporarios" / "concat.txt"
        manifest.write_text("".join("file '" + str(f.resolve()).replace("'", "'\\''")
                                    + "'\n" for f in normalized), encoding="utf-8")
        final = output_dir / f"E{episode_number:03d}-720p.mp4"
        if final.exists():
            raise StudioError("Episódio montado já existe; nenhuma sobrescrita automática")
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                        "-f", "concat", "-safe", "0", "-i", str(manifest),
                        "-c", "copy", "-movflags", "+faststart", str(final)],
                       check=True, timeout=180)
        if self._probe(final) != expected:
            raise StudioError("Arquivo final não corresponde a 720p")
        return {"status": "ok", "video": str(final), "resolution": "720p",
                "scenes": len(normalized), "note": "Montagem técnica; revise ritmo, diálogos e transições."}
