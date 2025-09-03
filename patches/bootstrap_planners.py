# --- bootstrap planners (add after app = Flask(...)) ---
from lilith.plan_engine import PlanRegistry, DeterministicPlanGenerator
from lilith.planner import deterministic_plan
from lilith.llm_plan import llm_generator

# Register engines
app.config["PLAN_REGISTRY"] = reg = PlanRegistry()
reg.register("deterministic", DeterministicPlanGenerator(deterministic_plan))
reg.register("llm", llm_generator)

# Default planner if none specified
app.config["DEFAULT_PLAN_ENGINE"] = "deterministic"

# (Optional) If you use Blueprints for routes below, remember to register them, e.g.:
# from lilith.routes_plan import plan_bp
# from lilith.routes_mirror import mirror_bp
# app.register_blueprint(plan_bp)
# app.register_blueprint(mirror_bp)
