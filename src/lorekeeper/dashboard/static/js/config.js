// ── Config tab ──
import { api, showToast } from "./api.js";
import { registerTab } from "./tab-registry.js";
import { esc } from "./utils.js";

// ── Self-register ──

registerTab("config", { load: loadConfig });

// ── Event listeners ──

document.addEventListener("app:config:save", () => saveConfig());
document.addEventListener("app:config:load", () => loadConfig());

export const CFG_FIELDS = {
	weights: [
		{
			key: "w_semantic",
			env: "LORE_W_SEMANTIC",
			label: "Semantic weight",
			desc: "Weight for vector similarity score",
			step: 0.01,
			type: "float",
		},
		{
			key: "w_keyword",
			env: "LORE_W_KEYWORD",
			label: "Keyword weight",
			desc: "Weight for BM25 keyword score",
			step: 0.01,
			type: "float",
		},
		{
			key: "w_memory",
			env: "LORE_W_MEMORY",
			label: "Memory score weight",
			desc: "Weight for stored memory quality score",
			step: 0.01,
			type: "float",
		},
		{
			key: "w_usage",
			env: "LORE_W_USAGE",
			label: "Usage weight",
			desc: "Weight for usage count normalised signal",
			step: 0.01,
			type: "float",
		},
	],
	quality: [
		{
			key: "score_bump_up",
			env: "LORE_SCORE_BUMP_UP",
			label: "Score bump up",
			desc: "Score delta on useful=True feedback",
			step: 0.01,
			type: "float",
		},
		{
			key: "score_bump_down",
			env: "LORE_SCORE_BUMP_DOWN",
			label: "Score bump down",
			desc: "Score delta on useful=False feedback",
			step: 0.01,
			type: "float",
		},
		{
			key: "score_min",
			env: "LORE_SCORE_MIN",
			label: "Score min",
			desc: "Minimum allowed score value",
			step: 0.1,
			type: "float",
		},
		{
			key: "score_max",
			env: "LORE_SCORE_MAX",
			label: "Score max",
			desc: "Maximum allowed score value",
			step: 0.1,
			type: "float",
		},
		{
			key: "new_memory_default_score",
			env: "LORE_NEW_MEMORY_DEFAULT_SCORE",
			label: "New memory default score",
			desc: "Default score for new memories",
			step: 5,
			type: "float",
		},
		{
			key: "soft_delete_confidence_threshold",
			env: "LORE_SOFT_DELETE_CONFIDENCE_THRESHOLD",
			label: "Soft delete threshold",
			desc: "Soft-delete when confidence drops to this",
			step: 1,
			type: "int",
		},
		{
			key: "confidence_window_size",
			env: "LORE_CONFIDENCE_WINDOW_SIZE",
			label: "Confidence window",
			desc: "EMA sliding window size for confidence",
			step: 1,
			type: "int",
		},
	],
	limits: [
		{
			key: "search_limit",
			env: "LORE_SEARCH_LIMIT",
			label: "Search result limit",
			desc: "Default number of memories returned by lore_search",
			step: 1,
			type: "int",
		},
		{
			key: "max_links_per_memory",
			env: "LORE_MAX_LINKS_PER_MEMORY",
			label: "Max links per memory",
			desc: "Max links returned per memory in search results (does not limit stored links)",
			step: 1,
			type: "int",
		},
		{
			key: "duplicate_threshold",
			env: "LORE_DUPLICATE_THRESHOLD",
			label: "Duplicate threshold",
			desc: "Combined score above which an insert is blocked as duplicate",
			step: 0.01,
			type: "float",
		},
		{
			key: "usage_normalisation_cap",
			env: "LORE_USAGE_NORMALISATION_CAP",
			label: "Usage normalisation cap",
			desc: "Cap for log-normalising usage_count in scoring",
			step: 1,
			type: "int",
		},
		{
			key: "decay_lambda",
			env: "LORE_DECAY_LAMBDA",
			label: "Decay lambda (λ)",
			desc: "Time-decay rate — higher = faster decay. Default 0.0077 ≈ 90-day half-life",
			step: 0.0001,
			type: "float",
		},
	],
	auto_link: [
		{
			key: "auto_link_enabled",
			env: "LORE_AUTO_LINK_ENABLED",
			label: "Auto-link enabled",
			desc: "When disabled, auto-link is a no-op for both remember() and insert()",
			type: "bool",
		},
		{
			key: "auto_link_k",
			env: "LORE_AUTO_LINK_K",
			label: "Auto-link K",
			desc: "Number of nearest neighbors to evaluate as auto-link candidates",
			step: 1,
			type: "int",
		},
		{
			key: "auto_link_threshold",
			env: "LORE_AUTO_LINK_THRESHOLD",
			label: "Auto-link threshold",
			desc: "Minimum cosine similarity score required to auto-link (default 0.85)",
			step: 0.01,
			type: "float",
		},
	],
	readonly: [
		{
			key: "data_dir",
			env: "LORE_DATA_DIR",
			label: "Data directory",
			desc: "Root path for Chroma + SQLite storage",
		},
		{
			key: "embedding_model",
			env: "LORE_EMBEDDING_MODEL",
			label: "Embedding model",
			desc: "Sentence-transformers model for semantic search",
		},
	],
	sweep: [
		{
			key: "suggest_interval_hours",
			env: "LORE_SUGGEST_INTERVAL_HOURS",
			label: "Sweep interval",
			desc: "Hours between automatic sweeps",
			step: 1,
			type: "int",
		},
		{
			key: "suggest_high_confidence_score",
			env: "LORE_SUGGEST_HIGH_CONFIDENCE_SCORE",
			label: "High confidence threshold",
			desc: "Min weighted score for 'high confidence' tag",
			step: 0.01,
			type: "float",
		},
		{
			key: "suggest_ttl_days",
			env: "LORE_SUGGEST_TTL_DAYS",
			label: "Suggestion TTL",
			desc: "Days before unactioned suggestions expire",
			step: 1,
			type: "int",
		},
	],
};

let _cfgOriginal = {};

export function _cfgRow(f, value, readonly) {
	const valHTML = readonly
		? `<span style="font-family:'SF Mono','Fira Code',monospace;font-size:12px;color:var(--muted)">${esc(String(value))}</span>`
		: f.type === "bool"
			? `<input type="checkbox" id="cfg-${f.key}" ${value ? "checked" : ""} data-change="config:change" style="width:20px;height:20px;accent-color:#0066ff;cursor:pointer">`
			: `<input type="number" id="cfg-${f.key}" value="${value}" step="${f.step}" data-input="config:change" style="width:110px">`;
	return `
    <div class="config-row">
      <div class="config-row-info">
        <div class="config-key">LORE_${f.env.replace("LORE_", "")}</div>
        <div class="config-desc">${f.desc || ""}</div>
      </div>
      <div class="config-val">${valHTML}</div>
    </div>`;
}

export function onCfgChange() {
	document.getElementById("cfg-unsaved").style.display = "inline";
}

document.addEventListener("app:config:change", () => onCfgChange());

document.addEventListener("app:sweep:trigger", async () => {
	try {
		await api("POST", "/api/sweep/trigger");
		showToast("Sweep triggered — will run within ~5 minutes");
		// Refresh status display
		_loadSweepStatus();
	} catch (e) {
		showToast(e.message, "error");
	}
});

export async function loadConfig() {
	let cfg;
	try {
		cfg = await api("GET", "/api/config");
	} catch (e) {
		showToast(e.message, "error");
		return;
	}
	_cfgOriginal = cfg;
	document.getElementById("cfg-unsaved").style.display = "none";
	document.getElementById("cfg-weights").innerHTML = CFG_FIELDS.weights
		.map((f) => _cfgRow(f, cfg[f.key], false))
		.join("");
	document.getElementById("cfg-quality").innerHTML = CFG_FIELDS.quality
		.map((f) => _cfgRow(f, cfg[f.key], false))
		.join("");
	document.getElementById("cfg-limits").innerHTML = CFG_FIELDS.limits
		.map((f) => _cfgRow(f, cfg[f.key], false))
		.join("");
	document.getElementById("cfg-auto-link").innerHTML = CFG_FIELDS.auto_link
		.map((f) => _cfgRow(f, cfg[f.key], false))
		.join("");
	document.getElementById("cfg-readonly").innerHTML = CFG_FIELDS.readonly
		.map((f) => _cfgRow(f, cfg[f.key], true))
		.join("");

	// Sweep config section
	document.getElementById("cfg-sweep").innerHTML = CFG_FIELDS.sweep
		.map((f) => _cfgRow(f, cfg[f.key] ?? "", false))
		.join("");

	// Fetch sweep status asynchronously
	_loadSweepStatus();
}

async function _loadSweepStatus() {
	try {
		const status = await api("GET", "/api/sweep/status");
		const roEl = document.getElementById("cfg-sweep-readonly");
		if (roEl) {
			roEl.innerHTML = `
        <div class="config-row" style="padding:6px 0;border-bottom:none">
          <div class="config-row-info">
            <div class="config-key" style="font-weight:400;color:var(--muted)">Last sweep</div>
          </div>
          <div class="config-val"><span style="font-family:'SF Mono',monospace;font-size:12px;color:var(--muted)">${status.last_run_at ? esc(`${status.last_run_at.replace("T", " ").split(".")[0]} UTC`) : "—"}</span></div>
        </div>
        <div class="config-row" style="padding:6px 0;border-bottom:none">
          <div class="config-row-info">
            <div class="config-key" style="font-weight:400;color:var(--muted)">Next sweep</div>
          </div>
          <div class="config-val"><span style="font-family:'SF Mono',monospace;font-size:12px;color:var(--muted)">${status.next_run_at ? esc(`${status.next_run_at.replace("T", " ").split(".")[0]} UTC`) : "—"}</span></div>
        </div>`;
		}
		const actionsEl = document.getElementById("cfg-sweep-actions");
		if (actionsEl) {
			actionsEl.innerHTML = `
        <button class="btn btn-primary btn-sm" data-action="sweep:trigger">Run Sweep Now</button>
        <span style="font-size:12px;color:var(--subtle)">Non-blocking — completes within ~5 min</span>`;
		}
	} catch {
		// Sweep status is a nice-to-have
	}
}

export async function saveConfig() {
	const body = {};
	for (const group of [
		CFG_FIELDS.weights,
		CFG_FIELDS.quality,
		CFG_FIELDS.limits,
		CFG_FIELDS.auto_link,
		CFG_FIELDS.sweep,
	]) {
		for (const f of group) {
			const el = document.getElementById(`cfg-${f.key}`);
			if (!el) continue;
			body[f.key] =
				f.type === "bool"
					? el.checked
					: f.type === "int"
						? parseInt(el.value, 10)
						: parseFloat(el.value);
		}
	}
	try {
		await api("PATCH", "/api/config", body);
		showToast("Config updated");
		document.getElementById("cfg-unsaved").style.display = "none";
		_cfgOriginal = { ..._cfgOriginal, ...body };
	} catch (e) {
		showToast(e.message, "error");
	}
}
