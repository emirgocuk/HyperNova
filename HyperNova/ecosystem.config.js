module.exports = {
    apps: [
        {
            name: "data_ingestor",
            script: "python",
            args: "data_layer/data_ingestor.py",
            interpreter: "none", // Since we pass "python" directly
            autorestart: true,
            watch: false,
            max_memory_restart: "1G",
            env: {
                PYTHONUNBUFFERED: "1"
            }
        },
        {
            name: "brain_service",
            script: "python",
            args: "ai_engine/brain_service.py",
            interpreter: "none",
            autorestart: true,
            watch: false,
            max_memory_restart: "2G", // AI Model requires more memory
            env: {
                PYTHONUNBUFFERED: "1"
            }
        },
        {
            name: "control_tower_api",
            script: "uvicorn",
            args: "control_tower.dashboard_api:app --host 0.0.0.0 --port 8000",
            interpreter: "none",
            autorestart: true,
            watch: false,
            max_memory_restart: "500M",
        }
    ]
};
