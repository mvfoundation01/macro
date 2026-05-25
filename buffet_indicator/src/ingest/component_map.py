"""Parse the LC v2.0 component-id map from the sealed pre-reg
— DRAFT_v4 §1 + §12 (seal 2a94417).

References
----------
- Sealed pre-reg §1: 5-component composite (z1..z5) catalog matching the
  v1.0 sealed catalog (z1=netfed_liquidity, z2=m2_growth_yoy,
  z3=banklend_growth_yoy, z4=dxy_inverse, z5=funding_stress).
- Sealed pre-reg §12: verdict JSON schema embeds ``component_id_map``
  with the canonical slugs verbatim — this function uses that block
  as the parse source of truth.
- Sealed pre-reg §11.1 line 739: function signature.
"""
from __future__ import annotations

import re
from pathlib import Path

EXPECTED_COMPONENT_IDS: tuple[str, ...] = ("z1", "z2", "z3", "z4", "z5")


class ComponentMapParseError(ValueError):
    """Raised when the sealed pre-reg's component_id_map cannot be parsed."""


def parse_component_id_map(spec_path: str) -> dict:
    """Parse the component-id map from a sealed pre-registration markdown.

    Reads the sealed §12 verdict JSON schema block (which embeds the
    ``component_id_map`` with the canonical slug-form names) and returns
    the 5-entry ``{z1..z5 -> slug}`` mapping.

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

    Raises
    ------
    ComponentMapParseError
        If the file cannot be read or the expected ``component_id_map``
        block is absent / malformed / missing any of z1..z5.

    References
    ----------
    Sealed pre-reg §1 + §12 + §11.1 line 739. Test: ``T18``.
    """
    path = Path(spec_path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ComponentMapParseError(
            f"could not read sealed pre-reg at {spec_path!r}: {exc}"
        ) from exc

    # Locate the embedded "component_id_map": { ... } JSON-style block.
    block_match = re.search(
        r'"component_id_map"\s*:\s*\{([^}]*)\}',
        text,
        flags=re.DOTALL,
    )
    if block_match is None:
        raise ComponentMapParseError(
            f"sealed pre-reg at {spec_path!r} does not contain a "
            "`component_id_map` block"
        )

    body = block_match.group(1)
    pair_re = re.compile(r'"(z[1-5])"\s*:\s*"([A-Za-z0-9_]+)"')
    mapping: dict[str, str] = {}
    for key, value in pair_re.findall(body):
        mapping[key] = value

    missing = [cid for cid in EXPECTED_COMPONENT_IDS if cid not in mapping]
    if missing:
        raise ComponentMapParseError(
            f"sealed component_id_map missing entries: {missing!r} "
            f"(parsed={mapping!r})"
        )

    return {cid: mapping[cid] for cid in EXPECTED_COMPONENT_IDS}
