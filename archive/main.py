def start_dungeon(self):
    record_timestamp = time.time()
    coordinates = []
    try:
        last_state = None
        while True:
            self.scan()

            if self.is_duty_found_window:
                time.sleep(1)
                self.accept_duty()
                time.sleep(5)

            if self.map_id != self.navigation_map_id:
                self.debounced_print(
                    'Map ID %s does not match expected %s, waiting.' % (self.map_id, self.navigation_map_id))
                time.sleep(1)
                continue

            if self.is_cutscene:
                time.sleep(1)
                self.skip_cutscene()
                time.sleep(5)
                continue

            if time.time() - record_timestamp > 0.1:
                coordinates.append((self.x, self.y, self.z))
                record_timestamp = time.time()

            if self.state_overall != last_state:
                print(self.state_overall)
            last_state = self.state_overall

            if self.state_overall == OverallState.ACQUIRING_TEAMMATE:
                if self.selection_acquired:
                    self.debounced_print('Selection acquired. Navigating to teammate')
                    self.init_routing_target([self.selection_x, self.selection_y])
                    self.state_overall = OverallState.NAVIGATING_TEAMMATE
                self.debounced_print('No selection. Attempting to select teammate and continue navigation')
                self.get_teammate()
                is_continue_walking = self.walk_to_routing_target()
                if not is_continue_walking:
                    self.debounced_print('Reached overall destination!')
                    break
                time.sleep(0.05)

            elif self.state_overall == OverallState.NAVIGATING_TEAMMATE:
                if not self.selection_acquired:
                    self.debounced_print('No selection. Attempting to select teammate')
                    self.get_teammate()
                    self.init_routing_target(self.navigation_target)
                    self.state_overall = OverallState.ACQUIRING_TEAMMATE
                    continue
                if self.selection_distance < self.max_distance_to_teammate:
                    self.debounced_print('Teammate in range. Attempting to select enemy')
                    self.cancel_routing_target()
                    self.get_teammate_target()
                    self.state_overall = OverallState.ACQUIRING_ENEMY
                    time.sleep(0.1)
                    continue
                self.debounced_print('Continue navigation towards teammate')
                is_continue_walking = self.walk_to_routing_target([self.selection_x, self.selection_y])
                if not is_continue_walking:
                    self.init_routing_target([self.selection_x, self.selection_y], continue_walking=True)
                    continue
                time.sleep(0.05)

            elif self.state_overall == OverallState.ACQUIRING_ENEMY:
                if not self.selection_acquired:
                    self.debounced_print('No selection. Attempting to select teammate')
                    self.get_teammate()
                    self.init_routing_target(self.navigation_target)
                    self.state_overall = OverallState.ACQUIRING_TEAMMATE
                    continue
                if not (self.selection_is_enemy and self.selection_is_damaged):
                    self.debounced_print('Selection is not a damaged enemy. Attempting to select teammate')
                    self.get_teammate()
                    self.init_routing_target(self.navigation_target)
                    self.state_overall = OverallState.ACQUIRING_TEAMMATE
                    continue
                self.state_overall = OverallState.NAVIGATING_ENEMY

            elif self.state_overall == OverallState.NAVIGATING_ENEMY:
                if not self.selection_acquired:
                    self.debounced_print('No selection. Attempting to select enemy')
                    self.get_teammate_target()
                    self.state_overall = OverallState.ACQUIRING_ENEMY
                    time.sleep(0.1)
                    continue
                if not (self.selection_is_enemy and self.selection_is_damaged):
                    self.debounced_print('Selection is not a damaged enemy. Attempting to select enemy')
                    self.get_teammate_target()
                    self.state_overall = OverallState.ACQUIRING_ENEMY
                    time.sleep(0.1)
                    continue
                if self.selection_distance > self.max_distance_to_target_high:
                    self.debounced_print('Enemy out of range. Attempting to select teammate')
                    self.get_teammate()
                    self.init_routing_target(self.navigation_target)
                    self.state_overall = OverallState.ACQUIRING_TEAMMATE
                    continue
                self.debounced_print('Enemy in range. Attempting to attack')
                self.state_overall = OverallState.ATTACKING

            elif self.state_overall == OverallState.ATTACKING:
                if not self.selection_acquired:
                    self.debounced_print('No selection. Attempting to select enemy')
                    self.get_teammate_target()
                    self.state_overall = OverallState.ACQUIRING_ENEMY
                    time.sleep(0.1)
                    continue
                if not (self.selection_is_enemy and self.selection_is_damaged):
                    self.debounced_print('Selection is not a damaged enemy. Attempting to select enemy')
                    self.get_teammate_target()
                    self.state_overall = OverallState.ACQUIRING_ENEMY
                    time.sleep(0.1)
                    continue
                if self.selection_distance > self.max_distance_to_target_high:
                    self.debounced_print('Enemy out of range. Attempting to select enemy')
                    self.get_teammate_target()
                    self.state_overall = OverallState.ACQUIRING_ENEMY
                    time.sleep(0.1)
                    continue
                if self.is_moving:
                    self.debounced_print('Still moving, waiting for stop')
                    time.sleep(0.1)
                    continue
                self.debounced_print('Enemy in range. Attacking!')
                self.attack()
                if self.selection_npc_id == 73:  # If Galvanth the dominator, target the DPS's target
                    self.debounced_print('Galvanth detected. Attempting to acquire DPS target')
                    self.get_dps_target()
                    OverallState.NAVIGATING_LAST_MILE

            elif self.state_overall == OverallState.NAVIGATING_LAST_MILE:
                if not self.selection_acquired:
                    self.debounced_print('No selection. Attempting to acquire enemy')
                    self.ensure_walking_state(False)
                    self.get_teammate_target()
                    self.state_overall = OverallState.ACQUIRING_ENEMY
                    continue
                if not (self.selection_is_enemy and self.selection_is_damaged):
                    self.debounced_print('Selection is not a damaged enemy. Attempting to select enemy')
                    self.get_teammate_target()
                    self.state_overall = OverallState.ACQUIRING_ENEMY
                    time.sleep(0.1)
                    continue
                if self.selection_distance < self.max_distance_to_target_high:
                    self.debounced_print('Enemy in range. Attempting to attack')
                    self.ensure_walking_state(False)
                    self.state_overall = OverallState.ATTACKING
                    continue
                self.debounced_print('Enemy out of range range. Attempting to approach enemy')
                self.turn_to_target(self.selection_x, self.selection_y)
                self.ensure_walking_state(True)
                time.sleep(0.1)
    finally:
        filename = 'recording%s.json' % (int(time.time() * 1000))
        with open(filename, 'w') as f:
            print('Writing %s waypoints to %s' % (len(coordinates), filename))
            f.write(json.dumps(coordinates))
