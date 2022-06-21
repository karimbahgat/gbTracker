# changeManager

API-only for receiving, storing, and sharing data on boundary changes. 

## Boundary References

- `BoundaryReference`:
  Referencing a boundary by a name or code, and one or more parent boundaries.
  - name
  - code_type
  - code
  - parent: Another boundaryReference. At least one required to reference the toplevel country, or zero if this is the toplevel. 

## Change types

- `boundarySnapshot`: A snapshot of what a boundary looked like at some point.
  - event: The temporal event during which this change occurred.
  - boundary_ref: A `BoundaryReference` instance.
  - geom: WKB/GeoJSON geometry definition.
  - source_type: Either a file reference or a map reference.
  - source: Link to the file or map object.
- `boundaryCreated`: No boundary existed in that area previously.
  - event: The temporal event during which this change occurred.
  - boundary_ref
  - snapshot: Reference to a boundarySnapshot after creation (optional).
- `boundaryTransfer`: Defines the transfer of territory between a pair of boundaries.
  - event: The temporal event during which this change occurred.
  - from_boundary
  - to_boundary
  - snapshot_before: Reference to a boundarySnapshot of from_boundary before the change (req if going backward).
  - snapshot_after: Reference to a boundarySnapshot of from_boundary after the change (req if going forward).
- `boundaryDissolved`: Boundary ceases to exist.
  - event: The temporal event during which this change occurred.
  - boundary_ref
  - snapshot: Reference to a boundarySnapshot prior to dissolving (optional).
- `nameChange`: A name changing.
- `codeChange`: A change in a boundary identifier.
- `parentChange`: A change in the parent boundary. 

Maybe:

- `nameCreated`
- `nameDeprecated`
- `codeCreated`
- `codeDeprecated`

## Events

- `Event` (contains one or more entries for `boundarySnapshot`,`boundaryCreated`,`boundaryTransfer`,`boundaryDissolved`,`nameChange`,`codeChange`):
  - date_start
  - date_end (optional)

Here are some recipes for events that can be captured using different combinations of change types:

- Boundary created (no boundary existed in that area previously):
  - A single `boundaryCreated` entry.
- Transfer of territory (territory is exchanged between two boundaries):
  - A single `boundaryTransfer` entry.
  - Cannot contain a `boundaryDissolved` entry.
- Annexation (a boundary is completely taken over by another):
  - A single `boundaryTransfer` entry.
  - A single `boundaryDissolved` entry where `from_boundary` references the annexed boundary.
- Breakaway (new boundary created from parts of another):
  - A single `boundaryCreated` entry.
  - A single `boundaryTransfer` entry where `to_boundary` references the new boundary.
- Dissolution (boundary is dissolved into two or more new component parts):
  - Two or more `boundaryCreated` entries.
  - The same number of `boundaryTransfer` entries where `to_boundary` references the new boundaries.
  - A single `boundaryDissolved` entry.
- Merger (two or more boundaries are merged into a new boundary):
  - A single `boundaryCreated` entry.
  - Two or more `boundaryTransfer` entries.
  - The same number of `boundaryDissolve` entries.
- Boundary dissolved (boundary ceases to exist):
  - A single `boundaryDissolve` entry.

## Advanced Examples

### Country swaps

Changes between country boundaries often, particularly when it comes to country mergers or breakups, leave the child ADM1 boundaries intact. In those cases it should be enough to change the parent of existing ADM1 boundaries. To do this one simply selects all ADM1 boundaries belonging to the country by configuring the boundary_ref, and registers a parentChange: 

- boundary_ref = BoundaryReference(country=A, children=[BoundaryReference()])
- ParentChange(event, boundary_ref, old_parent|new_parent)

OR

- BoundaryTransfer(event, fromAllInCountryA, toAllInCountryB)

hmm.....

And what if a boundary simple changed ownership from one country to another? 

- BoundaryInfo(event, boundary_before, boundary_after)

OR

- BoundaryTransfer(event, ADM1InCountryA, CountryB)

hmm.....

### Cross-level changes

There can be several ways to code the same event, depending on the available information. One could code it at a higher or a lower level, it should lead to the same results. E.g. if territory has been transferred from one ADM1 to another, one would typically code this as:

- BoundaryTransfer(event, from_boundary, to_boundary, before|after)

If however, we know that the territory transferred was a particular ADM2 boundary belonging to the ADM1 that lost territory, then we could code it as: 

- BoundaryTransfer(event, fromADM2, toADM1, before|after)
- BoundaryDissolved(event, fromADM2, before)
