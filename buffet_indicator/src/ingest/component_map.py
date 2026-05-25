"""Parse the LC v2.0 component-id map from the sealed pre-reg
— DRAFT_v4 §1 + §12 (seal 2a94417).

References
----------
- Sealed pre-reg §1: 5-component composite (z1..z5) catalog matching the
  v1.0 sealed catalog (z1=netfed_liquidity, z2=m2_growth_yoy,
  z3=banklend_growth_yoy, z4=dxy_inverse, z5=funding_stress).
- Sealed pre-reg §11.1 line 739: function signature.
"""
from __future__ import annotations


def parse_component_id_map(spec_path: str) -> dict:
    """Parse the component-id map from a sealed pre-registration markdown.

    Per §1 + §12 the canonical mapping is::

        {
          "z1": "netfed_liquidity",
          "z2": "m2_growth_yoy",
          "z3": "banklend_growth_yoy",
          "z4": "dxy_inverse",
          "z5": "funding_stress",
        }

    Parameters
    ----------
    spec_path : str
        Filesystem path to a sealed pre-reg markdown file.

    Returns
    -------
    dict
        Mapping ``{"z1": ..., ..., "z5": ...}``.

    References
    ----------
    Sealed pre-reg §1 + §12 + §11.1 line 739. Test: ``T18``.
    """
    raise NotImplementedError(
        "Scaffolded per PROMPT_CC_v11_4_v2_sprint_kickoff.md §3 "
        "- implement in subsequent phase"
    )
