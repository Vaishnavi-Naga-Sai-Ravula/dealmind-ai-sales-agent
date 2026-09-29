"""Transparent deterministic aid; this module does not claim to be an LLM."""
import re

from backend.models import Deal, Memory


def suggested_actions(deal: Deal, memories: list[Memory]) -> list[str]:
    evidence = [m.text for m in memories] + [i.content for i in deal.interactions[:3]]
    matches = []
    for text in evidence:
        for sentence in re.split(r'(?<=[.!?])\s+', text):
            if re.search(r'\b(need\w*|requir\w*|concern\w*|request\w*|prefer\w*|ask\w*|must|before)\b', sentence, re.I):
                action = f'Confirm with {deal.contact}: {sentence.strip()}'
                if action not in matches:
                    matches.append(action)
    return matches[:4] or [f'Ask {deal.contact} to confirm the decision criteria and next meeting date.']


def demo_brief(deal: Deal, memories: list[Memory]) -> str:
    lines = [f'{deal.company} · {deal.stage}', deal.summary]
    if deal.interactions:
        latest = deal.interactions[0]
        lines += [f'Latest recorded interaction ({latest.occurred_at.date()}):', latest.content]
    else:
        lines.append('No interactions recorded yet. Capture a discovery conversation to establish context.')
    if memories:
        lines += ['Historical evidence retrieved from Hindsight:']
        lines += [f'[{m.id}] {m.text}' for m in memories[:5]]
    else:
        lines.append('No historical memory available. This brief uses current CRM records only.')
    return '\n\n'.join(lines)
