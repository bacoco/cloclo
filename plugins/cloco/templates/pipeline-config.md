# Pipeline Config

## Verification

base_ref: main
verification_commands:
  - # npm test
  - # pytest tests/
  - # cargo test
  - # go test ./...

## Browser Testing (optional)

# browser_base_url: http://localhost:3000
# screenshot_output_dir: public/screenshots/
# browser_tool: playwright

## Deploy (optional)

# deploy_commands:
#   - docker compose up -d --build
