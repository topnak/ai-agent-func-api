# Azure Function: RunAgent

This repository contains a Python Azure Function named `RunAgent`.

Below are step-by-step instructions to run the function locally on Windows (PowerShell) and how to deploy it to Azure.

## Prerequisites
- Python 3.8 through 3.11 installed and on PATH (recommended)

### Python compatibility
This project is tested with Python 3.8, 3.9, 3.10 and 3.11. It is NOT compatible with Python 3.12 or newer due to runtime/worker incompatibilities with the Azure Functions Python worker at the time of writing. Please use a supported Python version when creating the virtual environment for local runs and when configuring the Function App runtime in Azure.
- Azure Functions Core Tools (v4) installed: https://learn.microsoft.com/azure/azure-functions/functions-run-local

```powershell
npm install -g azure-functions-core-tools@4 --unsafe-perm true
# then open a NEW terminal so PATH refreshes
func --version
```

- Azure CLI installed and logged in (az login): https://learn.microsoft.com/cli/azure/install-azure-cli
- (Optional) Visual Studio Code with the Azure Functions extension

## Files of note
- `RunAgent/` - function folder containing `__init__.py`, `function.json`, and `__pycache__/`.
- `host.json` - Function host configuration
- `local.settings.json` - local-only settings (not checked into source control)
- `requirements.txt` - Python dependencies

## Running locally (PowerShell)

1. Open PowerShell in the project root (`c:\code\ai-agent-func`).

2. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
pip install -r requirements.txt
```

4. Ensure you have a `local.settings.json` file in the project root. You can copy the provided template and customize it:

```powershell
cp .\local.settings.json.template .\local.settings.json
# then edit local.settings.json to fill real values
```

Template keys include `AzureWebJobsStorage` and `FUNCTIONS_WORKER_RUNTIME`. Do NOT commit `local.settings.json` to source control — the file is listed in `.gitignore`.

5. Start the function host:

```powershell
func start
```

6. Test the function
- The function route(s) are defined in `RunAgent/function.json`. Use curl, Postman, or a browser to call the endpoint shown by the Functions host output.

## Deploy to Azure

There are multiple ways to deploy. The steps below show how to use the Azure CLI + Functions Core Tools. Replace placeholders with your values.

1. Log in to Azure (if not already):

```powershell
az login
```

2. Create a resource group (if needed):

```powershell
az group create --name MyResourceGroup --location eastus
```

3. Create a storage account (required for Functions):

```powershell
az storage account create --name mystorageacct123 --location eastus --resource-group MyResourceGroup --sku Standard_LRS
```

4. Create a Function App (Python). Choose the runtime and SKU you need; example creates a Consumption plan Function App:

```powershell
az functionapp create --resource-group MyResourceGroup --consumption-plan-location eastus --runtime python --runtime-version 3.9 --functions-version 4 --name MyUniqueFunctionAppName --storage-account mystorageacct123
```

5. Deploy using Functions Core Tools (from project root):

```powershell
func azure functionapp publish MyUniqueFunctionAppName
```

6. (Optional) Set Application Settings (secrets, connection strings):

```powershell
az functionapp config appsettings set --name MyUniqueFunctionAppName --resource-group MyResourceGroup --settings "MySetting=MyValue"
```

7. Verify
- Browse to https://MyUniqueFunctionAppName.azurewebsites.net and call the function endpoint.

## VS Code deploy (alternative)
1. Open workspace in VS Code.
2. Install the Azure Functions and Azure Account extensions.
3. Sign in to Azure from the Azure sidebar.
4. Right-click the Function App in the Azure panel or use the command palette: 'Azure Functions: Deploy to Function App'.

## Notes & Troubleshooting
- If you get errors starting `func start`, ensure the Functions Core Tools version supports Python worker and that `FUNCTIONS_WORKER_RUNTIME` is set to `python` in `local.settings.json`.
- For local storage emulation, consider installing Azurite or use `UseDevelopmentStorage=true` for the AzureWebJobsStorage setting.
- Ensure `requirements.txt` matches the runtime Python version used by the Function App in Azure.


