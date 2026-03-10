"""Seed data for legal-service — NDA template + 11 clause categories.

Provides get_template_seed() and get_clause_seeds() for loading into
DocumentTemplate and TemplateClause records respectively.
"""

from uuid import uuid4


def _uid() -> str:
  return str(uuid4())


# --- NDA Template (Jinja2 content) ---

NDA_TEMPLATE_CONTENT = """# {{ title }}

**Date:** {{ effective_date }}

**Between:**

1. **{{ party_a.legal_name }}** (registered number {{ party_a.registration_number }}), whose registered office is at {{ party_a.address }} ("{{ party_a.label }}")

2. **{{ party_b.legal_name }}** (registered number {{ party_b.registration_number }}), whose registered office is at {{ party_b.address }} ("{{ party_b.label }}")

(each a "Party" and together the "Parties")

---

## 1. Definitions and Interpretation

In this Agreement, unless the context otherwise requires:

"**Confidential Information**" means all information (whether written, oral, visual or electronic) disclosed by one Party (the "Disclosing Party") to the other Party (the "Receiving Party") that is designated as confidential or that reasonably should be understood to be confidential given the nature of the information and circumstances of disclosure.

"**Purpose**" means {{ clauses.purpose }}

"**Representatives**" means the officers, directors, employees, agents, and professional advisors of a Party.

## 2. Obligations of Confidentiality

2.1 The Receiving Party shall:

- keep the Confidential Information strictly confidential;
- not disclose the Confidential Information to any person other than as permitted under this Agreement;
- use the Confidential Information solely for the Purpose;
- apply to the Confidential Information no lesser security measures and degree of care than those which the Receiving Party applies to its own confidential information.

## 3. Data Protection

{{ clauses.data_protection }}

## 4. Permitted Recipients

{{ clauses.permitted_recipients }}

## 5. Duration

{{ clauses.duration }}

## 6. Survival of Confidentiality Obligations

{{ clauses.confidentiality_survival }}

## 7. Return or Destruction of Information

{{ clauses.return_destruction }}

## 8. AI and Machine Learning Restrictions

{{ clauses.ai_ml_restrictions }}

## 9. Non-Solicitation

{{ clauses.non_solicitation }}

## 10. Governing Law

{{ clauses.governing_law }}

## 11. Dispute Resolution

{{ clauses.dispute_resolution }}

{% if clauses.additional %}
## 12. Additional Provisions

{% for clause in clauses.additional %}
### {{ clause.title }}

{{ clause.content }}

{% endfor %}
{% endif %}

## Signatures

This Agreement has been entered into on the date stated at the beginning of it.

**Signed** for and on behalf of **{{ party_a.legal_name }}**

Name: {{ party_a.signatory_name }}
Title: {{ party_a.signatory_role }}
Signature: ______________________________

**Signed** for and on behalf of **{{ party_b.legal_name }}**

Name: {{ party_b.signatory_name }}
Title: {{ party_b.signatory_role }}
Signature: ______________________________
"""


# --- Clause Definitions (11 categories) ---

CLAUSE_SEEDS = [
  {
    'id': None,  # auto-generated
    'name': 'Purpose',
    'category': 'purpose',
    'description': 'Defines the purpose for sharing confidential information.',
    'default_variant': 'B',
    'sort_order': 1,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': 'General Business',
        'content': 'exploring a potential business relationship between the Parties.',
      },
      'B': {
        'label': 'Business Collaboration',
        'content': 'exploring potential business collaboration and the exchange of confidential information relating to each Party\'s business operations, technology, and strategic plans.',
      },
      'C': {
        'label': 'Investment Evaluation',
        'content': 'evaluating a potential investment by one Party in the other, including due diligence review of financial, operational, and legal information.',
      },
      'D': {
        'label': 'Merger or Acquisition',
        'content': 'evaluating a potential merger, acquisition, or other business combination transaction between the Parties.',
      },
    },
  },
  {
    'id': None,
    'name': 'Data Protection',
    'category': 'data_protection',
    'description': 'Data protection and GDPR compliance terms.',
    'default_variant': 'A',
    'sort_order': 2,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': 'Standard Compliance',
        'content': 'Each Party shall comply with all applicable data protection legislation, including the UK GDPR and the Data Protection Act 2018, in connection with any personal data processed under or in connection with this Agreement.',
      },
      'B': {
        'label': 'GDPR with DPA',
        'content': 'The Parties acknowledge that personal data may be shared as part of the Confidential Information. Each Party shall comply with the UK GDPR and shall enter into a separate Data Processing Agreement if the processing of personal data is anticipated to be substantial or ongoing.',
      },
      'C': {
        'label': 'No Personal Data',
        'content': 'The Parties confirm that no personal data (as defined in the UK GDPR) shall be shared under this Agreement. If either Party inadvertently receives personal data, it shall notify the other Party and delete or return the data promptly.',
      },
    },
  },
  {
    'id': None,
    'name': 'Duration',
    'category': 'duration',
    'description': 'Duration of the confidentiality agreement.',
    'default_variant': 'A',
    'sort_order': 3,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': '2 Years',
        'content': 'This Agreement shall remain in force for a period of two (2) years from the date hereof, unless terminated earlier by either Party giving thirty (30) days\' written notice to the other Party.',
      },
      'B': {
        'label': '3 Years',
        'content': 'This Agreement shall remain in force for a period of three (3) years from the date hereof, unless terminated earlier by either Party giving sixty (60) days\' written notice to the other Party.',
      },
      'C': {
        'label': '5 Years',
        'content': 'This Agreement shall remain in force for a period of five (5) years from the date hereof, unless terminated earlier by mutual written agreement of the Parties.',
      },
      'D': {
        'label': '1 Year',
        'content': 'This Agreement shall remain in force for a period of one (1) year from the date hereof, unless terminated earlier by either Party giving fourteen (14) days\' written notice to the other Party.',
      },
    },
  },
  {
    'id': None,
    'name': 'Confidentiality Survival',
    'category': 'confidentiality_survival',
    'description': 'How long confidentiality obligations survive after termination.',
    'default_variant': 'A',
    'sort_order': 4,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': '2 Years Post-Termination',
        'content': 'The obligations of confidentiality set out in this Agreement shall survive its termination or expiry and shall continue in full force and effect for a period of two (2) years following such termination or expiry.',
      },
      'B': {
        'label': '3 Years Post-Termination',
        'content': 'The obligations of confidentiality set out in this Agreement shall survive its termination or expiry and shall continue in full force and effect for a period of three (3) years following such termination or expiry.',
      },
      'C': {
        'label': '5 Years Post-Termination',
        'content': 'The obligations of confidentiality set out in this Agreement shall survive its termination or expiry and shall continue in full force and effect for a period of five (5) years following such termination or expiry.',
      },
      'D': {
        'label': 'Indefinite with Trade Secret Protection',
        'content': 'The obligations of confidentiality set out in this Agreement shall survive its termination or expiry indefinitely, provided that obligations with respect to information that constitutes a trade secret shall continue for so long as such information remains a trade secret under applicable law.',
      },
    },
  },
  {
    'id': None,
    'name': 'Permitted Recipients',
    'category': 'permitted_recipients',
    'description': 'Who may receive the confidential information.',
    'default_variant': 'B',
    'sort_order': 5,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': 'Employees Only',
        'content': 'The Receiving Party may disclose Confidential Information only to those of its employees who have a need to know for the Purpose and who are bound by obligations of confidentiality no less onerous than those contained in this Agreement.',
      },
      'B': {
        'label': 'Employees and Professional Advisors',
        'content': 'The Receiving Party may disclose Confidential Information to its employees and professional advisors (including legal counsel, accountants, and financial advisors) who have a need to know for the Purpose, provided such persons are bound by obligations of confidentiality no less onerous than those contained in this Agreement.',
      },
      'C': {
        'label': 'Employees, Advisors, and Affiliates',
        'content': 'The Receiving Party may disclose Confidential Information to its employees, professional advisors, and affiliated companies (being companies which directly or indirectly control, are controlled by, or are under common control with the Receiving Party), provided all such persons are bound by obligations of confidentiality no less onerous than those contained in this Agreement.',
      },
      'D': {
        'label': 'Named Individuals Only',
        'content': 'The Receiving Party may disclose Confidential Information only to those specific individuals named in writing by the Disclosing Party, and such individuals must execute individual confidentiality undertakings in the form approved by the Disclosing Party.',
      },
    },
  },
  {
    'id': None,
    'name': 'Return or Destruction',
    'category': 'return_destruction',
    'description': 'What happens to confidential information on termination.',
    'default_variant': 'B',
    'sort_order': 6,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': 'Return All',
        'content': 'Upon termination or expiry of this Agreement, or upon the Disclosing Party\'s written request, the Receiving Party shall promptly return all Confidential Information, including all copies, extracts, and summaries thereof, to the Disclosing Party.',
      },
      'B': {
        'label': 'Destroy and Certify',
        'content': 'Upon termination or expiry of this Agreement, or upon the Disclosing Party\'s written request, the Receiving Party shall promptly destroy all Confidential Information in its possession, including all copies, extracts, and summaries thereof, and shall provide written certification of such destruction signed by an authorised officer.',
      },
      'C': {
        'label': 'Return or Destroy at Election',
        'content': 'Upon termination or expiry of this Agreement, or upon the Disclosing Party\'s written request, the Receiving Party shall, at the Disclosing Party\'s election, either return or destroy all Confidential Information. The Receiving Party may retain one archival copy solely for compliance and legal purposes, subject to ongoing confidentiality obligations.',
      },
    },
  },
  {
    'id': None,
    'name': 'AI/ML Restrictions',
    'category': 'ai_ml_restrictions',
    'description': 'Restrictions on use of confidential information for AI/ML purposes.',
    'default_variant': 'A',
    'sort_order': 7,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': 'Full Prohibition',
        'content': 'The Receiving Party shall not use any Confidential Information, directly or indirectly, to train, develop, fine-tune, or otherwise create or improve any artificial intelligence model, machine learning algorithm, large language model, or similar technology, without the prior written consent of the Disclosing Party.',
      },
      'B': {
        'label': 'Internal Analysis Only',
        'content': 'The Receiving Party may use Confidential Information for internal analytical purposes using artificial intelligence or machine learning tools, provided that: (a) such use is solely for the Purpose; (b) no Confidential Information is retained in or accessible through any model or algorithm; and (c) the Disclosing Party provides prior written consent.',
      },
      'C': {
        'label': 'No Restriction',
        'content': 'Subject to the other terms of this Agreement, there are no specific restrictions on the use of Confidential Information in connection with artificial intelligence or machine learning technologies, provided that any such use complies with the confidentiality obligations herein.',
      },
    },
  },
  {
    'id': None,
    'name': 'Dispute Resolution',
    'category': 'dispute_resolution',
    'description': 'How disputes arising from the agreement are resolved.',
    'default_variant': 'C',
    'sort_order': 8,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': 'English Courts',
        'content': 'Any dispute arising out of or in connection with this Agreement shall be subject to the exclusive jurisdiction of the courts of England and Wales.',
      },
      'B': {
        'label': 'Mediation then Litigation',
        'content': 'Any dispute arising out of or in connection with this Agreement shall first be referred to mediation under the CEDR Model Mediation Procedure. If the dispute is not resolved within sixty (60) days of the commencement of mediation, either Party may commence proceedings in the courts of England and Wales.',
      },
      'C': {
        'label': 'LCIA Arbitration',
        'content': 'Any dispute arising out of or in connection with this Agreement, including any question regarding its existence, validity, or termination, shall be referred to and finally resolved by arbitration under the LCIA Rules, which rules are deemed to be incorporated by reference. The number of arbitrators shall be one. The seat of arbitration shall be London. The language of the arbitration shall be English.',
      },
      'D': {
        'label': 'Agreed Jurisdiction',
        'content': 'Any dispute arising out of or in connection with this Agreement shall be subject to the exclusive jurisdiction of the courts of the jurisdiction agreed between the Parties and specified in the Governing Law clause.',
      },
      'E': {
        'label': 'Senior Management Escalation',
        'content': 'Any dispute arising out of or in connection with this Agreement shall first be escalated to the senior management of each Party for resolution. If the dispute is not resolved within thirty (30) days of such escalation, either Party may refer the dispute to arbitration under the LCIA Rules or commence proceedings in the courts of England and Wales.',
      },
    },
  },
  {
    'id': None,
    'name': 'Non-Solicitation',
    'category': 'non_solicitation',
    'description': 'Restrictions on soliciting or hiring the other party\'s employees.',
    'default_variant': 'A',
    'sort_order': 9,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'A': {
        'label': '12 Months',
        'content': 'During the term of this Agreement and for a period of twelve (12) months following its termination, neither Party shall, directly or indirectly, solicit or hire any employee of the other Party who was involved in the Purpose, without the prior written consent of the other Party.',
      },
      'B': {
        'label': '24 Months',
        'content': 'During the term of this Agreement and for a period of twenty-four (24) months following its termination, neither Party shall, directly or indirectly, solicit, entice away, or hire any employee or contractor of the other Party who was involved in discussions or activities under this Agreement.',
      },
      'C': {
        'label': '6 Months Key Personnel',
        'content': 'During the term of this Agreement and for a period of six (6) months following its termination, neither Party shall, directly or indirectly, solicit or hire any key personnel (being directors, officers, or senior managers) of the other Party who were involved in the Purpose.',
      },
      'D': {
        'label': 'No Restriction',
        'content': 'This Agreement does not restrict either Party from soliciting or hiring employees of the other Party, provided that any such hiring does not involve the use or disclosure of Confidential Information.',
      },
    },
  },
  {
    'id': None,
    'name': 'Governing Law',
    'category': 'governing_law',
    'description': 'Which jurisdiction\'s laws govern the agreement.',
    'default_variant': 'england_wales',
    'sort_order': 10,
    'is_required': True,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'england_wales': {
        'label': 'England and Wales',
        'content': 'This Agreement and any dispute or claim arising out of or in connection with it or its subject matter or formation (including non-contractual disputes or claims) shall be governed by and construed in accordance with the law of England and Wales.',
      },
      'scotland': {
        'label': 'Scotland',
        'content': 'This Agreement and any dispute or claim arising out of or in connection with it shall be governed by and construed in accordance with Scots law.',
      },
      'new_york': {
        'label': 'New York',
        'content': 'This Agreement shall be governed by and construed in accordance with the laws of the State of New York, United States of America, without regard to its conflict of laws provisions.',
      },
      'delaware': {
        'label': 'Delaware',
        'content': 'This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, United States of America, without regard to its conflict of laws provisions.',
      },
    },
  },
  {
    'id': None,
    'name': 'Additional Clauses',
    'category': 'additional',
    'description': 'Optional additional provisions that may be included.',
    'default_variant': 'no_partnership',
    'sort_order': 11,
    'is_required': False,
    'applicable_document_types': ['mutual_nda', 'one_way_nda'],
    'variants': {
      'no_partnership': {
        'label': 'No Partnership',
        'content': 'Nothing in this Agreement creates a partnership, joint venture, agency, or employment relationship between the Parties. Neither Party has any authority to bind or commit the other Party.',
      },
      'no_obligation': {
        'label': 'No Obligation to Proceed',
        'content': 'Nothing in this Agreement obliges either Party to enter into any further agreement, transaction, or business relationship. Each Party reserves the right to terminate discussions at any time without liability.',
      },
      'publicity': {
        'label': 'Publicity Restrictions',
        'content': 'Neither Party shall make any public announcement, press release, or other public disclosure regarding the existence or terms of this Agreement, or the discussions between the Parties, without the prior written consent of the other Party.',
      },
      'residual_info': {
        'label': 'Residual Information',
        'content': 'Nothing in this Agreement shall prevent either Party from using any ideas, concepts, know-how, or techniques that are retained in the unaided memory of individuals who have had access to Confidential Information, provided that such use does not involve the disclosure of the Confidential Information itself.',
      },
    },
  },
]


def get_template_seed() -> dict:
  """Return the NDA template seed data ready for DocumentTemplate creation.

  Returns:
    Dict with all fields needed to create a DocumentTemplate record.
  """
  return {
    'name': 'Mutual NDA (England & Wales)',
    'document_type': 'mutual_nda',
    'jurisdiction': 'england_wales',
    'description': 'Mutual Non-Disclosure Agreement template governed by the laws of England and Wales. Includes 11 configurable clause categories with multiple variants.',
    'template_content': NDA_TEMPLATE_CONTENT,
    'configuration_schema': {
      'required': [
        'purpose_option', 'personal_data_sharing', 'agreement_duration',
        'confidentiality_survival', 'permitted_recipients', 'return_or_destruction',
        'ai_ml_restrictions', 'governing_law', 'dispute_resolution', 'non_solicitation',
      ],
      'optional': ['additional_clauses', 'purpose'],
    },
    'is_active': True,
    'clause_ids': [],  # populated after clause creation
  }


def get_clause_seeds() -> list[dict]:
  """Return all 11 clause category seeds ready for TemplateClause creation.

  Returns:
    List of dicts, each with fields for a TemplateClause record.
  """
  return [
    {
      'name': clause['name'],
      'category': clause['category'],
      'description': clause['description'],
      'variants': clause['variants'],
      'default_variant': clause['default_variant'],
      'applicable_document_types': clause['applicable_document_types'],
      'sort_order': clause['sort_order'],
      'is_required': clause['is_required'],
    }
    for clause in CLAUSE_SEEDS
  ]


def get_clause_variants_dict() -> dict[str, dict[str, str]]:
  """Build the clause_variants dict expected by TemplateEngine.

  Returns:
    Dict mapping category -> {variant_key: content_string}.
    e.g. {'purpose': {'A': 'exploring...', 'B': 'exploring potential...'}}
  """
  result = {}
  for clause in CLAUSE_SEEDS:
    result[clause['category']] = {
      key: variant['content']
      for key, variant in clause['variants'].items()
    }
  return result
