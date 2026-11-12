# AWS role for the CI eval job

The `eval` job in `.github/workflows/ci.yml` assumes `rag-eval-ci` through GitHub OIDC. No key is stored in GitHub.

- `eval-role-trust.json`: only pushes to `staging` of this repo can assume the role.
- `eval-role-policy.json`: the role can call only Nova Lite and Titan Text Embeddings v2 in `us-east-1`.

Create it once:

```bash
aws iam create-role --role-name rag-eval-ci --assume-role-policy-document file://.github/aws/eval-role-trust.json
aws iam put-role-policy --role-name rag-eval-ci --policy-name bedrock-invoke --policy-document file://.github/aws/eval-role-policy.json
```
