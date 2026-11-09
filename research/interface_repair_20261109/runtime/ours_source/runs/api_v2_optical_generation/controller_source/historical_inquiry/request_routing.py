"""Shared request envelope for explicit learning and analysis dispatch."""
import copy


def service_request(answer):
    """Route explicit requests without rewriting plans or the researcher's result."""
    request = copy.deepcopy(answer.get('learning_request', {'needed': False}))
    if not isinstance(request, dict) or type(request.get('needed')) is not bool:
        raise ValueError('learning_request.needed must be a boolean')
    for key in ('queries', 'urls', 'source_ids', 'record_ids', 'operations'):
        if not isinstance(request.get(key, []), list):
            raise ValueError('Request ' + key + ' must be an array')
    operations = request.get('operations', [])
    plans = answer.get('analysis_plan')
    if plans is None:
        plans = []
    elif isinstance(plans, dict):
        plans = [plans]
    elif not isinstance(plans, list):
        raise ValueError('analysis_plan must be a plan object, array of objects, or null')
    merged, routes, declined = [], [], []
    for field, values in (('learning_request.operations', operations), ('analysis_plan', plans)):
        for i, plan in enumerate(values):
            if not isinstance(plan, dict):
                raise ValueError(field + ' must contain plan objects')
            # A declined empty placeholder is not an executable plan. A real plan
            # with kind/expression/other action fields still routes even if needed=false.
            if plan.get('needed') is False and set(plan) <= {'needed', 'reason', 'gap', 'why_now'}:
                declined.append({'field': field, 'index': i, 'plan': copy.deepcopy(plan)})
                continue
            # Exact equality only: do not infer equivalent scientific questions/expressions.
            duplicate = plan in merged
            if not duplicate:
                merged.append(copy.deepcopy(plan))
            routes.append({'field': field, 'index': i, 'operation_index': merged.index(plan),
                           'deduplicated': duplicate})
    knowledge_requested = request['needed']
    if not knowledge_requested:
        # A computation must not accidentally activate a declined literature search.
        request['queries'], request['urls'] = [], []
        request.pop('knowledge', None)
    request['operations'] = merged
    request['needed'] = knowledge_requested or bool(merged)
    routing = {'knowledge_requested': knowledge_requested, 'routes': routes}
    if declined:
        routing['declined_placeholders'] = declined
    return request, routing
