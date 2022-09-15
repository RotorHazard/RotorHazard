#
# Event Structure
# Provides methods for running race events and event formats
#

class EventStructure():
    
    def generate_bracket_positions(self, num_brackets, slots, participants):
        brackets = []
        for idx in range(num_brackets):
            bracket = {
                'stages': []
                }

            brackets.append(bracket)

            level = 0
            stage_max_participants = slots
            while participants > stage_max_participants:
                bracket['stages'].append(self.build_bracket_stage(level, stage_max_participants, slots))
                level += 1
                stage_max_participants = slots * (2 ** level)

            bracket['stages'].append(self.build_bracket_stage(level, stage_max_participants, slots, participants))

        return brackets

    def build_bracket_stage(self, level, stage_max_participants, slots, participants=0):
        num_advance = slots // 2
        # num_eliminate = slots % 2

        stage = []

        heat_idx = -2

        if participants:
            total_heats = int(stage_max_participants / slots)
            for _h in range(total_heats):
                stage.append([])

            for idx in range(total_heats):
                heat = stage[idx]

                def seed_slots(heat, idx, seed_slot_stage):
                    if (seed_slot_stage % 2):
                        heat.append({
                                'seed': (seed_slot_stage * total_heats) + total_heats - idx
                            })
                        heat.append({
                                'seed': stage_max_participants - (seed_slot_stage * total_heats) - total_heats + idx + 1
                            })
                    else:
                        heat.append({
                                'seed': (seed_slot_stage * total_heats) + idx + 1
                            })
                        heat.append({
                                'seed': stage_max_participants - (seed_slot_stage * total_heats) - idx
                            })

                for seed_slot_stage in range(int(slots / 2)):
                    seed_slots(heat, idx, seed_slot_stage)

            if slots % 2:
                final_seed_stage = (slots // 2)
                for idx in range(total_heats):
                    stage[idx].append({
                        'seed': (final_seed_stage * total_heats) + total_heats - idx
                        })

        else:
            for idx in range(stage_max_participants):
                slot = idx % slots
                if slot == 0:
                    heat = []
                    stage.append(heat)
                    heat_idx += 2
    
                if slot < num_advance:
                    heat.append({
                        'rank': slot + 1,
                        'stage': level + 1,
                        'heat': heat_idx
                        })
                else:
                    heat.append({
                        'rank': (slot - num_advance) + 1,
                        'stage': level + 1,
                        'heat': heat_idx + 1
                        })

        return stage
