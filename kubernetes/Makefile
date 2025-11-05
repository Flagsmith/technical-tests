.PHONY: run help clean

# Default target
help:
	@echo "Available commands:"
	@echo "  make run    - Start the Flagsmith interview challenge system"
	@echo "  make clean  - Clean up Docker resources"
	@echo "  make help   - Show this help message"

# Clean up project resources
clean:
	@echo "🧹 Cleaning up k8s_challenger resources..."
	-docker-compose down --volumes --remove-orphans
	-docker ps -a --filter "name=k8s_challenger" --format "{{.ID}}" | xargs -r docker rm -f
	-docker volume ls --filter "name=k8s_challenger" --format "{{.Name}}" | xargs -r docker volume rm
	@echo "✅ Cleanup complete"

# Start the interview system with cleanup before and after
run: clean
	@echo "🚀 Starting Flagsmith Interview Challenge System..."
	# Build images
	docker-compose build cli candidate-env
	# Start k3s in background
	docker-compose up -d k3s
	# Run CLI interactively
	docker-compose run --rm cli
	# Cleanup when done
	$(MAKE) clean
	@echo "✅ Session complete"