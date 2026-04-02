"""Email drafting tool — generates professional client emails for Extremo Ambiente."""

from __future__ import annotations

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Template structures (bilingual PT-PT / EN)
# ---------------------------------------------------------------------------

_TEMPLATES = {
    "proposal": {
        "pt": {
            "name": "Proposta de Evento",
            "structure": (
                "ESTRUTURA DA PROPOSTA:\n"
                "1. Assunto do email (claro e profissional)\n"
                "2. Saudação personalizada ao cliente\n"
                "3. Parágrafo de abertura — agradecer o contacto e resumir o pedido\n"
                "4. Resumo do evento:\n"
                "   - Data proposta\n"
                "   - Dimensão do grupo\n"
                "   - Local/região\n"
                "   - Duração estimada\n"
                "5. Itinerário proposto (tabela com horários e atividades):\n"
                "   - Hora | Atividade | Local | Duração\n"
                "   - Incluir tempos de deslocação entre paragens\n"
                "6. Serviços incluídos:\n"
                "   - Transporte (tipo de veículo)\n"
                "   - Guias especializados\n"
                "   - Seguros e equipamentos\n"
                "   - Refeições/degustações (se aplicável)\n"
                "7. Notas sobre preços (estrutura geral, sem valores específicos a menos que mencionados na conversa)\n"
                "8. Próximos passos (reunião, chamada, confirmação)\n"
                "9. Fecho profissional"
            ),
        },
        "en": {
            "name": "Event Proposal",
            "structure": (
                "PROPOSAL STRUCTURE:\n"
                "1. Email subject line (clear and professional)\n"
                "2. Personalized greeting to the client\n"
                "3. Opening paragraph — thank them for reaching out and summarize the request\n"
                "4. Event overview:\n"
                "   - Proposed date\n"
                "   - Group size\n"
                "   - Location/region\n"
                "   - Estimated duration\n"
                "5. Proposed itinerary (table with time slots and activities):\n"
                "   - Time | Activity | Location | Duration\n"
                "   - Include travel times between stops\n"
                "6. Included services:\n"
                "   - Transportation (vehicle type)\n"
                "   - Specialized guides\n"
                "   - Insurance and equipment\n"
                "   - Meals/tastings (if applicable)\n"
                "7. Pricing notes (general structure, no specific values unless mentioned in conversation)\n"
                "8. Next steps (meeting, call, confirmation)\n"
                "9. Professional sign-off"
            ),
        },
    },
    "follow_up": {
        "pt": {
            "name": "Follow-up",
            "structure": (
                "ESTRUTURA DO FOLLOW-UP:\n"
                "1. Assunto do email (referência ao contacto anterior)\n"
                "2. Saudação personalizada\n"
                "3. Referir o contacto/reunião anterior e o evento discutido\n"
                "4. Resumo breve dos pontos principais acordados\n"
                "5. Perguntar se há dúvidas ou alterações pretendidas\n"
                "6. Reforçar disponibilidade para adaptar a proposta\n"
                "7. Sugerir próximo passo concreto (chamada, reunião, confirmação)\n"
                "8. Fecho caloroso e profissional"
            ),
        },
        "en": {
            "name": "Follow-up",
            "structure": (
                "FOLLOW-UP STRUCTURE:\n"
                "1. Email subject line (reference to previous contact)\n"
                "2. Personalized greeting\n"
                "3. Reference previous contact/meeting and the event discussed\n"
                "4. Brief summary of the key points agreed upon\n"
                "5. Ask if there are any questions or desired changes\n"
                "6. Reinforce availability to adapt the proposal\n"
                "7. Suggest a concrete next step (call, meeting, confirmation)\n"
                "8. Warm and professional sign-off"
            ),
        },
    },
    "confirmation": {
        "pt": {
            "name": "Confirmação de Evento",
            "structure": (
                "ESTRUTURA DA CONFIRMAÇÃO:\n"
                "1. Assunto do email (confirmação + nome do evento/empresa)\n"
                "2. Saudação personalizada\n"
                "3. Confirmação entusiástica do evento\n"
                "4. Detalhes logísticos confirmados:\n"
                "   - Data e hora de início/fim\n"
                "   - Ponto de encontro/pickup\n"
                "   - Número de participantes\n"
                "   - Contacto no local\n"
                "5. Itinerário final confirmado\n"
                "6. O que os participantes devem trazer/vestir\n"
                "7. Informações de contacto de emergência\n"
                "8. Política de cancelamento (se aplicável)\n"
                "9. Fecho com entusiasmo pelo evento"
            ),
        },
        "en": {
            "name": "Event Confirmation",
            "structure": (
                "CONFIRMATION STRUCTURE:\n"
                "1. Email subject line (confirmation + event/company name)\n"
                "2. Personalized greeting\n"
                "3. Enthusiastic event confirmation\n"
                "4. Confirmed logistics:\n"
                "   - Date and start/end time\n"
                "   - Meeting point/pickup location\n"
                "   - Number of participants\n"
                "   - On-site contact person\n"
                "5. Final confirmed itinerary\n"
                "6. What participants should bring/wear\n"
                "7. Emergency contact information\n"
                "8. Cancellation policy (if applicable)\n"
                "9. Enthusiastic sign-off about the upcoming event"
            ),
        },
    },
    "thank_you": {
        "pt": {
            "name": "Agradecimento Pós-Evento",
            "structure": (
                "ESTRUTURA DO AGRADECIMENTO:\n"
                "1. Assunto do email (agradecimento + referência ao evento)\n"
                "2. Saudação personalizada\n"
                "3. Agradecer pela confiança e participação\n"
                "4. Destacar um momento memorável do evento (se conhecido)\n"
                "5. Pedir feedback ou avaliação\n"
                "6. Mencionar disponibilidade para futuros eventos\n"
                "7. Oferecer desconto/condição especial para próximo evento (se apropriado)\n"
                "8. Fecho caloroso"
            ),
        },
        "en": {
            "name": "Post-Event Thank You",
            "structure": (
                "THANK YOU STRUCTURE:\n"
                "1. Email subject line (thank you + event reference)\n"
                "2. Personalized greeting\n"
                "3. Thank them for their trust and participation\n"
                "4. Highlight a memorable moment from the event (if known)\n"
                "5. Request feedback or review\n"
                "6. Mention availability for future events\n"
                "7. Offer a discount/special condition for next event (if appropriate)\n"
                "8. Warm sign-off"
            ),
        },
    },
}

# ---------------------------------------------------------------------------
# Branding / signature blocks
# ---------------------------------------------------------------------------

_BRANDING = {
    "pt": {
        "greeting": "Caro/a",
        "sign_off": "Com os melhores cumprimentos",
        "company_line": "Extremo Ambiente — Turismo de Aventura",
        "tagline": "Experiências únicas na natureza portuguesa",
        "contact": "info@extremoambiente.com | +351 XXX XXX XXX | www.extremoambiente.com",
    },
    "en": {
        "greeting": "Dear",
        "sign_off": "Best regards",
        "company_line": "Extremo Ambiente — Adventure Tourism",
        "tagline": "Unique experiences in Portuguese nature",
        "contact": "info@extremoambiente.com | +351 XXX XXX XXX | www.extremoambiente.com",
    },
}

_TONE_GUIDANCE = {
    "professional": "Warm but professional. Confident and organized.",
    "friendly": "Warm, enthusiastic, and approachable. Use a conversational style.",
    "formal": "Formal and respectful. Suitable for first contact or official proposals.",
}


@tool
def draft_email(
    context: str,
    language: str = "pt",
    tone: str = "professional",
    template: str = "general",
) -> str:
    """Draft a professional client email for Extremo Ambiente.

    This tool returns structured prompt instructions that the agent should use
    to compose the email directly. The agent (LLM) generates the actual email
    text based on the context and template guidance provided.

    Args:
        context: What the email should contain — e.g. 'proposal for 25 people
            corporate event in Porto on March 15 with jeep tour and wine tasting',
            'follow up on Vodafone team building proposal'. Be as specific as
            possible with event details.
        language: 'pt' for Portuguese (Portugal) or 'en' for English.
            Defaults to 'pt'.
        tone: 'professional', 'friendly', or 'formal'. Defaults to 'professional'.
        template: Type of email to generate. Options:
            - 'proposal' — Full event proposal with itinerary and services
            - 'follow_up' — Follow-up after initial contact
            - 'confirmation' — Event confirmation with logistics
            - 'thank_you' — Post-event thank you
            - 'general' — Free-form email (default, no specific template)
    """
    lang = language if language in ("pt", "en") else "pt"
    lang_label = "Portuguese (Portugal)" if lang == "pt" else "English"
    branding = _BRANDING[lang]
    tone_text = _TONE_GUIDANCE.get(tone, _TONE_GUIDANCE["professional"])

    # Build the base instructions
    lines = [
        "DRAFT EMAIL INSTRUCTIONS:",
        f"- Language: {lang_label}",
        f"- Tone: {tone_text}",
        f"- Context: {context}",
        f"- Greeting style: {branding['greeting']}",
        f"- Sign-off: {branding['sign_off']}",
        f"- Company signature: {branding['company_line']}",
        f"- Company tagline: {branding['tagline']}",
        f"- Contact info: {branding['contact']}",
    ]

    # Add template-specific structure if applicable
    tpl = _TEMPLATES.get(template)
    if tpl:
        tpl_lang = tpl[lang]
        lines.append(f"\nTEMPLATE: {tpl_lang['name']}")
        lines.append(f"\n{tpl_lang['structure']}")
    else:
        # General email — basic instructions
        lines.extend([
            "",
            "GENERAL EMAIL GUIDELINES:",
            "- Include a subject line",
            "- Keep it concise (3-5 paragraphs max)",
            "- Mention Extremo Ambiente by name",
            "- If discussing activities/places, reference specific ones from the conversation",
        ])

    lines.extend([
        "",
        "BRANDING REQUIREMENTS:",
        "- Always include the company signature block at the end",
        "- Use the company tagline in the signature",
        "- Reference specific Extremo Ambiente services discussed in conversation",
        "- Maintain the brand voice: adventurous yet professional",
        "",
        "Now compose the full email based on these instructions and the conversation context.",
    ])

    return "\n".join(lines)
