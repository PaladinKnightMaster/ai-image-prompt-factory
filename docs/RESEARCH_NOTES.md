# Research Notes and Evidence Boundaries

**Research pass:** 2026-09-07

These notes document the first evidence-backed V3 foundation. Module files contain source links and confidence labels. The goal is not to turn V3.0 into an art-history encyclopedia; it is to make uncertain knowledge explicit and prevent obvious period/material collapse.

## GPT Image 2

Official OpenAI material consulted for the adapter describes GPT Image 2 as the current high-end image generation/editing model, with strong instruction following, structured layouts/text rendering, and high-fidelity image inputs. V3 therefore targets one adapter deeply and keeps API execution conservative.

- https://platform.openai.com/docs/models/gpt-image-2
- https://openai.com/index/introducing-our-latest-image-generation-model-in-the-api/

## China

### Han

The Met’s Han overview provides the Western/Eastern Han split, Chang’an/Luoyang context, trade/exchange, and representative earthenware/tomb/material objects. The pack deliberately avoids inventing one universal Han hairstyle or dress pattern from broad period labels.

- https://www.metmuseum.org/essays/han-dynasty-206-b-c-220-a-d

### Tang

The Met’s 8th-century seated court lady provides a concrete court-costume/material example and evidence of Tang cosmopolitan exchange through the imported stool form. The V3 pack treats “Tang princess” as a user role request rather than proof that any attractive court subject should receive imperial status.

- https://www.metmuseum.org/art/collection/search/75765

### Song

The first-pass Song pack is deliberately cautious: it separates ink/calligraphy/ceramic traditions from later Ming/Qing signatures and requires Northern/Southern Song narrowing for strict work.

- https://www.metmuseum.org/toah/hd/song/hd_song.htm

### Ming

The Met Ming overview directly shows diverse evidence families including ink painting, ink/color on silk, silk embroidery, huanghuali furniture, pipa, and Jingdezhen cobalt porcelain. V&A’s blue-and-white overview supports the underglaze cobalt process and Jingdezhen development.

- https://www.metmuseum.org/essays/ming-dynasty-1368-1644
- https://www.vam.ac.uk/articles/chinese-blue-and-white-ceramics

### Qing

Met court-robe objects support Manchu adaptations, narrow sleeves/horse-hoof cuffs, standardized court dress and rank-specific iconography. The pack therefore warns against casually placing imperial symbols on generic subjects.

- https://www.metmuseum.org/art/collection/search/68295
- https://www.metmuseum.org/art/collection/search/69066

### Dunhuang / Mogao

UNESCO documents the multi-century Mogao cave complex and its extensive murals and cross-cultural significance. V3 models Dunhuang as a site/tradition pack rather than a dynasty. Strict reconstruction must narrow subperiod/cave/evidence family.

- https://whc.unesco.org/en/list/440

## Japan

### Heian

A Met Edo-period porcelain object depicting a Heian court woman explicitly notes the long flowing hair and multilayered clothing associated with Heian court women. Because this is later retrospective representation, V3 marks some cosmetic/conventional details as interpretive unless supported by tighter evidence.

- https://www.metmuseum.org/art/collection/search/46509

### Edo / ukiyo-e

The Met’s ukiyo-e technical essay is especially useful for the art-method engine: designer/carver/printer/publisher collaboration, cherry-wood blocks, mulberry paper, separate blocks for colors, and registration. The module uses these production constraints rather than treating ukiyo-e as a flat-line digital filter.

- https://www.metmuseum.org/essays/woodblock-prints-in-the-ukiyo-e-style

## Mediterranean

The Greek/Hellenistic/Roman packs are foundations rather than exhaustive chronologies. Two rules are especially important in V3:

- Classical and Hellenistic sculptural language should not be merged into one “Greek statue” preset.
- ancient marble should not automatically be described as originally pure white; evidence for polychromy must remain available.

- https://www.metmuseum.org/perspectives/articles/2022/7/chroma-ancient-sculpture-in-color
- https://www.metmuseum.org/toah/hd/haht/hd_haht.htm
- https://www.metmuseum.org/toah/hd/ropo/hd_ropo.htm

## Art / craft methods

### Watercolor

The Met’s materials/techniques article supports water-based pigment, transparent behavior and paper as a primary support. V3 treats reserved paper, wash transparency and edge variation as defining behavior rather than “soft pastel painting.”

- https://www.metmuseum.org/perspectives/materials-and-techniques-drawing-watercolor

### Blue-and-white ceramic

V&A supports brush-applied cobalt pigment on a white ceramic body under transparent glaze. V3 therefore requires surface curvature, glaze-over-decoration light response, and culture-specific motif selection.

- https://www.vam.ac.uk/articles/chinese-blue-and-white-ceramics

### Japanese woodblock

The Met process essay supports the carved/printed production model used by the module.

- https://www.metmuseum.org/essays/woodblock-prints-in-the-ukiyo-e-style

### Layered paper

A British Museum Tang-period paper flower from Cave 17 is made from multiple superimposed paper layers, cut, painted and pasted; the curator notes folded/cut/unfolded construction for related examples. This is a useful historical anchor for physically plausible layered-paper logic.

- https://www.britishmuseum.org/collection/object/A_1919-0101-0-230-2

### Manuscript miniature

Met manuscript leaves demonstrate tempera and gold leaf on parchment and page-specific hierarchy. V3’s module is intentionally generic across manuscript traditions and requires culture/period narrowing for strict historical work.

- https://www.metmuseum.org/art/collection/search/461161

### Bronze

Getty’s bronze technical-examination resources inform the module’s casting/join/chasing/patina emphasis.

- https://www.getty.edu/publications/bronze-guidelines/

## Important non-claims

V3.0 does **not** claim that:

- every field in an era pack is exhaustive;
- one surviving art object represents all people in a dynasty;
- later retrospective images are equivalent to contemporary documentary evidence;
- image-generation success proves historical authenticity;
- “Dunhuang,” “wuxia,” “xianxia,” or “ancient China” are single eras.

Those boundaries are intentional product features, not missing polish.
