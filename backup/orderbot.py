from pocketflow import Node, Flow
import yaml
import os

# Minimal LLM wrapper
def call_llm(prompt):
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    r = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return r.choices[0].message.content

# Shared store to maintain context
shared = {}

# Node to detect intent
class DetectIntent(Node):
    def prep(self, shared):
        user_input = shared.get("user_input", "")
        return user_input

    def exec(self, user_input):
        prompt = f"""
You are an assistant. Detect the user's intent and classify it into one of the following: 
"order_food", "query_status", "cancel_order". 
Input: {user_input}
Respond in YAML format:
```yml
intent: <detected_intent>
reason: <why this intent>
```
"""
        response = call_llm(prompt)
        try:
            # Try to find the YAML content between ```yml and ``` markers
            if "```yml" in response and "```" in response:
                yaml_str = response.split("```yml")[1].split("```")[0].strip()
            else:
                yaml_str = response.strip()
            return yaml.safe_load(yaml_str)
        except Exception as e:
            print(f"Error parsing response: {response}")
            return {"intent": "unknown", "reason": "Failed to parse response"}

    def post(self, shared, prep_res, exec_res):
        shared["intent"] = exec_res["intent"]
        shared["reason"] = exec_res["reason"]
        return exec_res["intent"]

# Node to extract entities
class ExtractEntities(Node):
    def prep(self, shared):
        return shared.get("user_input", ""), shared["intent"]

    def exec(self, inputs):
        user_input, intent = inputs
        prompt = f"""
You are an assistant helping extract entities for actions. 
For intent '{intent}', extract relevant entities.
Input: {user_input}
Respond in YAML format:
```yml
entities:
  - name: <entity_name>
    value: <entity_value>
```
"""
        response = call_llm(prompt)
        yaml_str = response.split("```yml")[1].split("```")[0].strip()
        return yaml.safe_load(yaml_str)

    def post(self, shared, prep_res, exec_res):
        shared["entities"] = exec_res["entities"]
        return "default"

# Node to map to an action
class MapAction(Node):
    def prep(self, shared):
        return shared["intent"], shared["entities"]

    def exec(self, inputs):
        intent, entities = inputs
        if intent == "order_food":
            food_item = next((e['value'] for e in entities if e['name'] == "food_item"), "unknown")
            size = next((e['value'] for e in entities if e['name'] == "size"), "regular")
            return f"AddToCart('{food_item}', '{size}')"
        elif intent == "query_status":
            order_id = next((e['value'] for e in entities if e['name'] == "order_id"), "unknown")
            return f"QueryOrderStatus('{order_id}')"
        elif intent == "cancel_order":
            order_id = next((e['value'] for e in entities if e['name'] == "order_id"), "unknown")
            return f"CancelOrder('{order_id}')"
        else:
            return "UnknownAction()"

    def post(self, shared, prep_res, exec_res):
        shared["action"] = exec_res
        return "default"

# Node to execute action
class ExecuteAction(Node):
    def prep(self, shared):
        return shared["action"]

    def exec(self, action):
        # Simulate execution, e.g., calling an API
        print(f"Executing action: {action}")
        return f"Action executed: {action}"

    def post(self, shared, prep_res, exec_res):
        shared["result"] = exec_res
        print(exec_res)

# Connecting nodes
intent_node = DetectIntent()
entity_node = ExtractEntities()
map_action_node = MapAction()
execute_node = ExecuteAction()

intent_node - "order_food" >> entity_node
intent_node - "query_status" >> entity_node
intent_node - "cancel_order" >> entity_node
entity_node >> map_action_node >> execute_node

# Run the flow
flow = Flow(start=intent_node)

# Test the chatbot
shared["user_input"] = "I want to order a large hamburger"
flow.run(shared)
