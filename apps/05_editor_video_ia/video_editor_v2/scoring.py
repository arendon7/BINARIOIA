
ROLE_WEIGHTS={"hook":1.25,"main_idea":1.20,"argument":1.05,"evidence":1.08,"example":.95,"context":.90,"cta":1.12,"closing":1.05,"transition":.70,"other":.75,"filler":.10,"repetition":.08}
def segment_score(seg):
    semantic=.48*max(0,min(1,seg.relevance))+.27*max(0,min(1,seg.clarity))+.17*max(0,min(1,seg.energy))+.08*(1 if seg.must_keep else 0)
    penalty=.65*max(0,min(1,seg.redundancy))
    return max(0,(semantic-penalty)*ROLE_WEIGHTS.get(seg.role,.75))
